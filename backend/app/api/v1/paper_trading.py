from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.models.paper_trade import PaperTrade
from app.services.paper_trading_service import close_paper_trade, list_paper_trades, paper_summary, update_paper_trade
from app.services.paper_trading_orchestrator import PaperOrchestratorConfig, PaperTradingOrchestrator
from app.services.paper_market_service import PaperMarketCoordinator
from app.services.paper_dhan_service import run_dhan_paper_session
from app.services.paper_live_dhan_service import mark_dhan_paper_position
from app.services.intraday_evidence_aggregation import aggregate_paper_performance
from app.services.strategy_readiness import build_strategy_readiness
from app.services.strategy_qualification import QualificationPolicy, qualify_strategy
from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest
from app.services.intraday_strategy import IntradayConfig
from app.services.intraday_walk_forward import run_fixed_parameter_walk_forward
from app.services.intraday_robustness import run_robustness_analysis
from app.services.research_store import research_store
from app.services.intraday_scorecard import build_intraday_scorecard, ScorecardConfig
from app.services.intraday_evidence_aggregation import aggregate_scorecards
from app.services.strategy_paper_authorization import authorize_strategy, get_active_authorization, revoke_strategy

router = APIRouter(prefix="/paper-trading", tags=["Paper Trading"])
_sessions: dict[int, PaperTradingOrchestrator] = {}
_market: dict[int, PaperMarketCoordinator] = {}

class PaperTradeCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=30); quantity: int = Field(gt=0, le=1_000_000); entry_price: float = Field(gt=0); stop_price: float = Field(gt=0); target_price: float = Field(gt=0); strategy_version: str = Field(default="V1", pattern="^(V1|V2)$")
class PaperMarkRequest(BaseModel):
    price: float = Field(gt=0); high: float | None = Field(default=None, gt=0); low: float | None = Field(default=None, gt=0)
class PaperCloseRequest(BaseModel):
    exit_price: float = Field(gt=0); reason: str = Field(default="MANUAL", min_length=1, max_length=40)
class PaperSignalRequest(BaseModel):
    session: str = Field(min_length=1, max_length=40); action: str = Field(min_length=1, max_length=20); entry: float = Field(gt=0); stop: float = Field(gt=0); target: float = Field(gt=0); symbol: str = Field(min_length=1, max_length=30); interval: str = Field(default="5", pattern="^(1|5|15|25|60)$"); strategy_version: str = Field(default="V1", pattern="^(V1|V2)$"); lot_size: int = Field(default=1, gt=0, le=100000)
class PaperBarRequest(BaseModel):
    session: str = Field(min_length=1, max_length=40); high: float = Field(gt=0); low: float = Field(gt=0); close: float = Field(gt=0)
class MarketBarRequest(BaseModel):
    session: str = Field(min_length=1, max_length=40); symbol: str = Field(min_length=1, max_length=30); open: float = Field(gt=0); high: float = Field(gt=0); low: float = Field(gt=0); close: float = Field(gt=0); volume: float = Field(ge=0); opening_high: float | None = Field(default=None, gt=0); opening_low: float | None = Field(default=None, gt=0); interval: str = Field(default="5", pattern="^(1|5|15|25|60)$")
class DhanPaperRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=30); session: str = Field(min_length=10, max_length=10); interval: str = Field(default="5", pattern="^(1|5|15|25|60)$")


def _owned(db: Session, user_id: int, trade_id: int) -> PaperTrade:
    trade = db.query(PaperTrade).filter(PaperTrade.id == trade_id, PaperTrade.user_id == user_id).first()
    if trade is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper trade not found")
    return trade


def _orchestrator(user_id: int) -> PaperTradingOrchestrator:
    return _sessions.setdefault(user_id, PaperTradingOrchestrator(PaperOrchestratorConfig(trade_direction="LONG_ONLY")))


def _market_coordinator(user_id: int) -> PaperMarketCoordinator:
    return _market.setdefault(user_id, PaperMarketCoordinator(orchestrator=_orchestrator(user_id)))


def _research_rows(symbol: str, interval: str) -> list[dict]:
    dataset = f"nse/{symbol.strip().upper()}_intraday_{interval}m"
    bars = research_store.load(dataset)
    rows = []
    for bar in bars:
        row = bar.as_row(); row["session"] = row["timestamp"].date().isoformat(); rows.append(row)
    return rows


def _server_research_readiness(symbol: str, symbols: str, interval: str, strategy_version: str, paper_trades: list[PaperTrade]) -> dict:
    rows = _research_rows(symbol, interval)
    if not rows:
        return {"qualification": {"status": "NOT_QUALIFIED", "paper_trading_allowed": False, "reason": "NO_RESEARCH_DATA"}, "cross_stock": {"summary": {"robust_percent": 0.0, "symbols_tested": 0}}, "strategy_fingerprint": None}
    strategy = IntradayConfig()
    config = IntradayBacktestConfig(strategy=strategy, strategy_version=strategy_version)
    backtest = run_intraday_backtest(rows, config)
    robustness = run_robustness_analysis(rows, config, stress_costs=True)
    try:
        walk_forward = run_fixed_parameter_walk_forward(rows, 60, 20, None, config)
    except ValueError:
        walk_forward = {"windows": 0, "v2": {"windows": [], "summary": {}}}
    qualification = qualify_strategy(backtest, robustness, walk_forward, QualificationPolicy())
    requested = list(dict.fromkeys(item.strip().upper() for item in (symbols or symbol).split(",") if item.strip()))
    datasets = {item: _research_rows(item, interval) for item in requested}
    datasets = {item: data for item, data in datasets.items() if data}
    scorecard = build_intraday_scorecard(datasets, ScorecardConfig(minimum_trades=30, slippage_rate=config.slippage_rate))
    evidence = aggregate_scorecards(scorecard.get("ranked", []), interval=interval, requested_symbols=requested, missing_symbols=[item for item in requested if item not in datasets])
    readiness = build_strategy_readiness(qualification, evidence, paper_trades)
    return {"qualification": qualification, "cross_stock": evidence, "readiness": readiness, "strategy_fingerprint": backtest.get("strategy_fingerprint")}


def _authorize_from_research(db: Session, user_id: int, symbol: str, symbols: str, interval: str, strategy_version: str, paper_trades: list[PaperTrade]) -> dict[str, Any]:
    evidence = _server_research_readiness(symbol, symbols, interval, strategy_version, paper_trades)
    qualification = evidence["qualification"]
    fingerprint = evidence.get("strategy_fingerprint")
    if not qualification.get("paper_trading_allowed") or not fingerprint:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"reason": "STRATEGY_NOT_QUALIFIED", "qualification": qualification})
    record = authorize_strategy(db, user_id, symbol=symbol, interval=interval, strategy_version=strategy_version, fingerprint=fingerprint, evidence=evidence)
    _orchestrator(user_id).authorize_strategy(fingerprint=fingerprint)
    return {"authorized": True, "authorization_id": record.id, "symbol": record.symbol, "interval": record.interval, "strategy_version": record.strategy_version, "fingerprint": record.fingerprint, "authorized_at": record.authorized_at}


def _load_authorization(db: Session, user_id: int, symbol: str, interval: str, strategy_version: str) -> bool:
    record = get_active_authorization(db, user_id, symbol=symbol, interval=interval, strategy_version=strategy_version)
    if record is None:
        _orchestrator(user_id).revoke_strategy()
        return False
    _orchestrator(user_id).authorize_strategy(fingerprint=record.fingerprint)
    return True

@router.post("/trades", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
def create_paper_trade(payload: PaperTradeCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail="Direct paper-trade creation is disabled; use the server-controlled paper session signal pipeline.")

@router.get("/trades")
def get_paper_trades(status_filter: str | None = Query(default=None, alias="status", pattern="^(OPEN|CLOSED)$"), strategy_version: str | None = Query(default=None, pattern="^(V1|V2)$"), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    trades = list_paper_trades(db, current_user.id, status_filter)
    if strategy_version: trades = [trade for trade in trades if trade.strategy_version == strategy_version]
    return {"trades": trades, "summary": paper_summary(trades), "mode": "SIMULATION_ONLY"}

@router.get("/dashboard")
def paper_dashboard(strategy_version: str | None = Query(default=None, pattern="^(V1|V2)$"), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    trades = list_paper_trades(db, current_user.id)
    if strategy_version: trades = [trade for trade in trades if trade.strategy_version == strategy_version]
    performance = aggregate_paper_performance(trades); live = _orchestrator(current_user.id).summary()
    return {"mode":"SIMULATION_ONLY","summary":paper_summary(trades),"performance":performance,"live":live,
            "open_positions":[{"id":trade.id,"symbol":trade.symbol,"quantity":trade.quantity,"entry_price":trade.entry_price,"stop_price":trade.stop_price,"target_price":trade.target_price,"pnl":trade.pnl,"strategy_version":trade.strategy_version} for trade in trades if trade.status == "OPEN"],
            "risk":{"trade_direction":"LONG_ONLY","broker_orders_enabled":False,"max_daily_loss_enforced":True,"strategy_version_filter":strategy_version or "ALL"}}

@router.get("/readiness")
def paper_readiness(symbol: str = Query(min_length=1, max_length=30), symbols: str = Query(default="", max_length=2000), strategy_version: str = Query(default="V1", pattern="^(V1|V2)$"), interval: str = Query(default="5", pattern="^(1|5|15|25|60)$"), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    trades = list_paper_trades(db, current_user.id)
    filtered = [trade for trade in trades if trade.strategy_version == strategy_version]
    result = _server_research_readiness(symbol, symbols, interval, strategy_version, filtered)
    return {"mode":"SIMULATION_ONLY","strategy_version":strategy_version,"symbol":symbol.strip().upper(),"interval":interval,**result}

@router.post("/readiness/authorize")
def authorize_paper_readiness(symbol: str = Query(min_length=1, max_length=30), symbols: str = Query(default="", max_length=2000), strategy_version: str = Query(default="V1", pattern="^(V1|V2)$"), interval: str = Query(default="5", pattern="^(1|5|15|25|60)$"), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    trades = list_paper_trades(db, current_user.id)
    filtered = [trade for trade in trades if trade.strategy_version == strategy_version]
    return {"mode": "SIMULATION_ONLY", **_authorize_from_research(db, current_user.id, symbol, symbols, interval, strategy_version, filtered)}

@router.post("/readiness/revoke")
def revoke_paper_readiness(symbol: str = Query(min_length=1, max_length=30), strategy_version: str = Query(default="V1", pattern="^(V1|V2)$"), interval: str = Query(default="5", pattern="^(1|5|15|25|60)$"), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    revoked = revoke_strategy(db, current_user.id, symbol=symbol, interval=interval, strategy_version=strategy_version)
    _orchestrator(current_user.id).revoke_strategy()
    return {"mode": "SIMULATION_ONLY", "revoked": revoked}

@router.get("/performance")
def get_paper_performance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return aggregate_paper_performance(list_paper_trades(db, current_user.id))

@router.post("/trades/{trade_id}/mark")
def mark_paper_trade(trade_id: int, payload: PaperMarkRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    trade = _owned(db, current_user.id, trade_id)
    try: return update_paper_trade(db, trade, payload.price, market_high=payload.high, market_low=payload.low)
    except ValueError as exc: raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

@router.post("/trades/{trade_id}/close")
def close_trade(trade_id: int, payload: PaperCloseRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    trade = _owned(db, current_user.id, trade_id)
    try: return close_paper_trade(db, trade, payload.exit_price, payload.reason)
    except ValueError as exc: raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

@router.get("/session")
def paper_session_summary(current_user: User = Depends(get_current_user)) -> dict[str, Any]: return {"mode":"SIMULATION_ONLY",**_orchestrator(current_user.id).summary()}

@router.post("/session/signal")
def paper_session_signal(payload: PaperSignalRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    if not _load_authorization(db, current_user.id, payload.symbol, payload.interval, payload.strategy_version):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active qualified strategy authorization for this symbol and interval")
    return {"mode":"SIMULATION_ONLY",**_orchestrator(current_user.id).on_signal(payload.session,payload.model_dump())}

@router.post("/session/bar")
def paper_session_bar(payload: PaperBarRequest, current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    if payload.low > payload.high: raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="low cannot exceed high")
    return {"mode":"SIMULATION_ONLY",**_orchestrator(current_user.id).on_bar(payload.session,payload.high,payload.low,payload.close)}

@router.post("/session/live-ltp")
def paper_live_ltp(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    try: return mark_dhan_paper_position(db, current_user.id, _orchestrator(current_user.id))
    except ValueError as exc: raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except Exception as exc: raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

@router.post("/session/reset")
def paper_session_reset(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    orchestrator = PaperTradingOrchestrator(PaperOrchestratorConfig(trade_direction="LONG_ONLY"))
    _sessions[current_user.id] = orchestrator
    _market[current_user.id] = PaperMarketCoordinator(orchestrator=orchestrator)
    return {"mode":"SIMULATION_ONLY","reset":True}

@router.post("/session/market-bar")
def paper_market_bar(payload: MarketBarRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    if payload.low > payload.high: raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="low cannot exceed high")
    if not _load_authorization(db, current_user.id, payload.symbol, payload.interval, "V1"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active qualified strategy authorization for this symbol and interval")
    try: return _market_coordinator(current_user.id).on_bar(payload.session,payload.symbol,payload.open,payload.high,payload.low,payload.close,payload.volume,payload.opening_high,payload.opening_low)
    except ValueError as exc: raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

@router.post("/session/dhan")
def paper_dhan_session(payload: DhanPaperRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    if not _load_authorization(db, current_user.id, payload.symbol, payload.interval, "V1"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active qualified strategy authorization for this symbol and interval")
    try: return run_dhan_paper_session(db,current_user.id,payload.symbol,payload.session,payload.interval,coordinator=_market_coordinator(current_user.id))
    except ValueError as exc: raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except Exception as exc: raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

@router.post("/session/market-reset")
def paper_market_reset(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    _market[current_user.id] = PaperMarketCoordinator(orchestrator=_orchestrator(current_user.id)); return {"mode":"SIMULATION_ONLY","reset":True}
