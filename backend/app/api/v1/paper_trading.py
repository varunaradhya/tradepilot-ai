from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.paper_trading_service import close_paper_trade, list_paper_trades, open_paper_trade, paper_summary, update_paper_trade
from app.models.paper_trade import PaperTrade
from app.services.paper_trading_orchestrator import PaperOrchestratorConfig, PaperTradingOrchestrator
from app.services.paper_market_service import PaperMarketCoordinator
from app.services.paper_dhan_service import run_dhan_paper_session
from app.services.intraday_evidence_aggregation import aggregate_paper_performance
from app.services.strategy_readiness import build_strategy_readiness

router = APIRouter(prefix="/paper-trading", tags=["Paper Trading"])
_sessions: dict[int, PaperTradingOrchestrator] = {}
_market: dict[int, PaperMarketCoordinator] = {}


class PaperTradeCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=30)
    quantity: int = Field(gt=0, le=1_000_000)
    entry_price: float = Field(gt=0)
    stop_price: float = Field(gt=0)
    target_price: float = Field(gt=0)
    strategy_version: str = Field(default="V1", pattern="^(V1|V2)$")


class PaperMarkRequest(BaseModel):
    price: float = Field(gt=0)
    high: float | None = Field(default=None, gt=0)
    low: float | None = Field(default=None, gt=0)


class PaperCloseRequest(BaseModel):
    exit_price: float = Field(gt=0)
    reason: str = Field(default="MANUAL", min_length=1, max_length=40)


class PaperSignalRequest(BaseModel):
    session: str = Field(min_length=1, max_length=40)
    action: str = Field(min_length=1, max_length=20)
    entry: float = Field(gt=0)
    stop: float = Field(gt=0)
    target: float = Field(gt=0)
    symbol: str = Field(default="", max_length=30)
    lot_size: int = Field(default=1, gt=0, le=100000)


class PaperBarRequest(BaseModel):
    session: str = Field(min_length=1, max_length=40)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)


class MarketBarRequest(BaseModel):
    session: str = Field(min_length=1, max_length=40)
    symbol: str = Field(min_length=1, max_length=30)
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)
    opening_high: float | None = Field(default=None, gt=0)
    opening_low: float | None = Field(default=None, gt=0)


class DhanPaperRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=30)
    session: str = Field(min_length=10, max_length=10)
    interval: str = Field(default="5", pattern="^(1|5|15|25|60)$")


def _owned(db: Session, user_id: int, trade_id: int) -> PaperTrade:
    trade = db.query(PaperTrade).filter(PaperTrade.id == trade_id, PaperTrade.user_id == user_id).first()
    if trade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper trade not found")
    return trade


def _orchestrator(user_id: int) -> PaperTradingOrchestrator:
    return _sessions.setdefault(user_id, PaperTradingOrchestrator(PaperOrchestratorConfig(trade_direction="LONG_ONLY")))


def _market_coordinator(user_id: int) -> PaperMarketCoordinator:
    return _market.setdefault(user_id, PaperMarketCoordinator())


@router.post("/trades", status_code=status.HTTP_201_CREATED)
def create_paper_trade(payload: PaperTradeCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return open_paper_trade(db, current_user.id, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.get("/trades")
def get_paper_trades(status_filter: str | None = Query(default=None, alias="status", pattern="^(OPEN|CLOSED)$"), strategy_version: str | None = Query(default=None, pattern="^(V1|V2)$"), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    trades = list_paper_trades(db, current_user.id, status_filter)
    if strategy_version:
        trades = [trade for trade in trades if trade.strategy_version == strategy_version]
    return {"trades": trades, "summary": paper_summary(trades), "mode": "SIMULATION_ONLY"}


@router.get("/dashboard")
def paper_dashboard(strategy_version: str | None = Query(default=None, pattern="^(V1|V2)$"), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    trades = list_paper_trades(db, current_user.id)
    if strategy_version:
        trades = [trade for trade in trades if trade.strategy_version == strategy_version]
    performance = aggregate_paper_performance(trades)
    live = _orchestrator(current_user.id).summary()
    return {
        "mode": "SIMULATION_ONLY",
        "summary": paper_summary(trades),
        "performance": performance,
        "live": live,
        "open_positions": [
            {
                "id": trade.id,
                "symbol": trade.symbol,
                "quantity": trade.quantity,
                "entry_price": trade.entry_price,
                "stop_price": trade.stop_price,
                "target_price": trade.target_price,
                "pnl": trade.pnl,
                "strategy_version": trade.strategy_version,
            }
            for trade in trades if trade.status == "OPEN"
        ],
        "risk": {
            "trade_direction": "LONG_ONLY",
            "broker_orders_enabled": False,
            "max_daily_loss_enforced": True,
            "strategy_version_filter": strategy_version or "ALL",
        },
    }


@router.get("/readiness")
def paper_readiness(
    qualification_status: str = Query(default="PAPER_CANDIDATE", pattern="^(PAPER_CANDIDATE|NOT_QUALIFIED)$"),
    robust_percent: float = Query(default=0.0, ge=0, le=100),
    symbols_tested: int = Query(default=0, ge=0),
    strategy_version: str | None = Query(default=None, pattern="^(V1|V2)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    trades = list_paper_trades(db, current_user.id)
    if strategy_version:
        trades = [trade for trade in trades if trade.strategy_version == strategy_version]
    result = build_strategy_readiness({"status": qualification_status}, {"summary": {"symbols_tested": symbols_tested, "robust_percent": robust_percent}}, trades)
    return {"mode": "SIMULATION_ONLY", "strategy_version": strategy_version or "ALL", **result}


@router.get("/performance")
def get_paper_performance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    trades = list_paper_trades(db, current_user.id)
    return aggregate_paper_performance(trades)


@router.post("/trades/{trade_id}/mark")
def mark_paper_trade(trade_id: int, payload: PaperMarkRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    trade = _owned(db, current_user.id, trade_id)
    try:
        return update_paper_trade(db, trade, payload.price, market_high=payload.high, market_low=payload.low)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/trades/{trade_id}/close")
def close_trade(trade_id: int, payload: PaperCloseRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    trade = _owned(db, current_user.id, trade_id)
    try:
        return close_paper_trade(db, trade, payload.exit_price, payload.reason)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.get("/session")
def paper_session_summary(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    return {"mode": "SIMULATION_ONLY", **_orchestrator(current_user.id).summary()}


@router.post("/session/signal")
def paper_session_signal(payload: PaperSignalRequest, current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    result = _orchestrator(current_user.id).on_signal(payload.session, payload.model_dump())
    return {"mode": "SIMULATION_ONLY", **result}


@router.post("/session/bar")
def paper_session_bar(payload: PaperBarRequest, current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    if payload.low > payload.high:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="low cannot exceed high")
    result = _orchestrator(current_user.id).on_bar(payload.session, payload.high, payload.low, payload.close)
    return {"mode": "SIMULATION_ONLY", **result}


@router.post("/session/reset")
def paper_session_reset(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    _sessions[current_user.id] = PaperTradingOrchestrator(PaperOrchestratorConfig(trade_direction="LONG_ONLY"))
    return {"mode": "SIMULATION_ONLY", "reset": True}


@router.post("/session/market-bar")
def paper_market_bar(payload: MarketBarRequest, current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    if payload.low > payload.high:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="low cannot exceed high")
    try:
        return _market_coordinator(current_user.id).on_bar(payload.session, payload.symbol, payload.open, payload.high, payload.low, payload.close, payload.volume, payload.opening_high, payload.opening_low)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/session/dhan")
def paper_dhan_session(payload: DhanPaperRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        return run_dhan_paper_session(db, current_user.id, payload.symbol, payload.session, payload.interval, coordinator=_market_coordinator(current_user.id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/session/market-reset")
def paper_market_reset(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    _market[current_user.id] = PaperMarketCoordinator()
    return {"mode": "SIMULATION_ONLY", "reset": True}
