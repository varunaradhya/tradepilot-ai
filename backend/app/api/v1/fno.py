from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.brokers.dhan import DhanAPIError, DhanClient
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.paper_trade import PaperTrade
from app.services.broker_service import get_access_token, get_user_broker
from app.services.fno_execution import execute_fno_decision
from app.services.fno_strategy import FNOConfig, build_fno_decision, select_option_contracts
from app.services.fno_instrument_service import fno_instrument_master
from app.services.paper_trading_service import close_paper_trade, list_paper_trades, open_paper_trade, update_paper_trade

router = APIRouter(prefix="/fno", tags=["F&O"])


class OptionChainRequest(BaseModel):
    underlying_security_id: int = Field(gt=0)
    underlying_segment: str = Field(default="IDX_I", min_length=2, max_length=20)
    expiry: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class ExpiryRequest(BaseModel):
    underlying_security_id: int = Field(gt=0)
    underlying_segment: str = Field(default="IDX_I", min_length=2, max_length=20)


class FNODecisionRequest(BaseModel):
    underlying: dict[str, Any]
    direction: str
    option_chain: dict[str, Any]
    config: dict[str, Any] = {}


class FNOExecuteRequest(BaseModel):
    decision: dict[str, Any]
    correlation_id: str = Field(default="tradepilot-fno", max_length=30)


class FNOPaperOpenRequest(BaseModel):
    decision: dict[str, Any]
    strategy_version: str = Field(default="V1", pattern="^(V1|V2)$")


def _dhan(db, user_id: int) -> DhanClient:
    c = get_user_broker(db, user_id, "DHAN")
    if c is None:
        raise HTTPException(status_code=404, detail="Dhan is not connected.")
    return DhanClient(c.client_id, get_access_token(c))


def _ltp_from_response(response: dict[str, Any], security_id: str) -> float | None:
    data = response.get("data") if isinstance(response, dict) else None
    if not isinstance(data, dict):
        return None
    # Dhan marketfeed responses are segment -> security-id -> quote objects.
    for segment in ("NSE_FNO", "NSE_EQ", "NSE_FNO_OPTIONS"):
        segment_data = data.get(segment)
        if isinstance(segment_data, dict):
            quote = segment_data.get(str(security_id)) or segment_data.get(int(security_id)) if str(security_id).isdigit() else segment_data.get(str(security_id))
            if isinstance(quote, dict):
                for key in ("last_price", "LTP", "ltp"):
                    value = quote.get(key)
                    if value is not None:
                        try:
                            return float(value)
                        except (TypeError, ValueError):
                            pass
    # Be tolerant of a flat response in mocks/tests.
    quote = data.get(str(security_id))
    if isinstance(quote, dict):
        value = quote.get("last_price", quote.get("ltp"))
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None
    return None


@router.get("/underlyings")
def underlyings(q: str = Query(default="", max_length=50), current_user: User = Depends(get_current_user)):
    try:
        return [{"security_id": x.security_id, "exchange_segment": x.exchange_segment, "symbol": x.symbol, "name": x.name} for x in fno_instrument_master.search(q)]
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to load NSE F&O underlyings: {exc}") from exc


@router.post("/expiries")
def expiries(data: ExpiryRequest, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    try:
        return _dhan(db, current_user.id).option_expiries(data.underlying_security_id, data.underlying_segment)
    except DhanAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/chain")
def option_chain(data: OptionChainRequest, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    try:
        return _dhan(db, current_user.id).option_chain(data.underlying_security_id, data.underlying_segment, data.expiry)
    except DhanAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/scan")
def scan(data: FNODecisionRequest, current_user: User = Depends(get_current_user)):
    try:
        cfg = FNOConfig(**{k: v for k, v in data.config.items() if k in FNOConfig.__dataclass_fields__})
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    candidates = select_option_contracts(data.option_chain, data.direction, cfg)
    return {"candidates": candidates, "decision": build_fno_decision(data.underlying, data.direction, candidates, cfg), "mode": "PAPER_ONLY"}


@router.post("/paper/open")
def open_option_paper_trade(data: FNOPaperOpenRequest, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    decision = data.decision
    if decision.get("decision") != "QUALIFIED":
        raise HTTPException(status_code=422, detail="Only a QUALIFIED option decision can be paper traded.")
    contract = decision.get("contract") or {}
    underlying = decision.get("underlying") or {}
    security_id = contract.get("security_id")
    quantity = int(decision.get("quantity") or 0)
    lot_size = int(decision.get("lot_size") or 0)
    if not security_id or quantity <= 0 or lot_size <= 0 or quantity % lot_size:
        raise HTTPException(status_code=422, detail="Option decision has invalid security ID, quantity, or lot size.")
    existing = db.query(PaperTrade).filter(PaperTrade.user_id == current_user.id, PaperTrade.status == "OPEN", PaperTrade.asset_type == "OPTION", PaperTrade.security_id == str(security_id)).first()
    if existing:
        raise HTTPException(status_code=409, detail="A paper position for this option contract is already open.")
    symbol = f"{underlying.get('symbol', 'OPTION')} {underlying.get('expiry', '')} {contract.get('strike')} {contract.get('option_type')}".strip()
    try:
        trade = open_paper_trade(
            db,
            current_user.id,
            symbol=symbol[:30],
            quantity=quantity,
            entry_price=float(decision["entry"]),
            stop_price=float(decision["stop"]),
            target_price=float(decision["target"]),
            strategy_version=data.strategy_version,
            asset_type="OPTION",
            security_id=str(security_id),
            exchange_segment="NSE_FNO",
            underlying=str(underlying.get("symbol", "")).upper(),
            expiry=underlying.get("expiry"),
            strike=float(contract.get("strike")) if contract.get("strike") is not None else None,
            option_type=contract.get("option_type"),
            lot_size=lot_size,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"mode": "PAPER_ONLY", "position": {"id": trade.id, "symbol": trade.symbol, "underlying": trade.underlying, "expiry": trade.expiry, "strike": trade.strike, "option_type": trade.option_type, "security_id": trade.security_id, "quantity": trade.quantity, "entry_price": trade.entry_price, "stop_price": trade.stop_price, "target_price": trade.target_price, "pnl": trade.pnl, "status": trade.status}}


@router.get("/paper/positions")
def option_paper_positions(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    trades = [t for t in list_paper_trades(db, current_user.id, "OPEN") if t.asset_type == "OPTION"]
    if not trades:
        return {"mode": "PAPER_ONLY", "market_connected": False, "positions": []}
    client = _dhan(db, current_user.id)
    security_ids = [str(t.security_id) for t in trades if t.security_id]
    try:
        quotes = client.market_ltp("NSE_FNO", security_ids)
    except DhanAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    positions = []
    for trade in trades:
        ltp = _ltp_from_response(quotes, str(trade.security_id))
        if ltp is not None:
            trade = update_paper_trade(db, trade, ltp)
        positions.append({"id": trade.id, "symbol": trade.symbol, "underlying": trade.underlying, "expiry": trade.expiry, "strike": trade.strike, "option_type": trade.option_type, "security_id": trade.security_id, "quantity": trade.quantity, "entry_price": trade.entry_price, "last_price": ltp, "stop_price": trade.stop_price, "target_price": trade.target_price, "pnl": trade.pnl, "status": trade.status, "reason": trade.reason})
    return {"mode": "PAPER_ONLY", "market_connected": True, "positions": positions}


@router.post("/paper/positions/{trade_id}/close")
def close_option_paper_trade(trade_id: int, exit_price: float = Query(gt=0), current_user: User = Depends(get_current_user), db=Depends(get_db)):
    trade = db.query(PaperTrade).filter(PaperTrade.id == trade_id, PaperTrade.user_id == current_user.id, PaperTrade.asset_type == "OPTION").first()
    if trade is None:
        raise HTTPException(status_code=404, detail="Option paper position not found")
    try:
        trade = close_paper_trade(db, trade, exit_price, "MANUAL")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"mode": "PAPER_ONLY", "position": {"id": trade.id, "status": trade.status, "exit_price": trade.exit_price, "pnl": trade.pnl, "reason": trade.reason}}


@router.post("/execute")
def execute(data: FNOExecuteRequest, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    try:
        return execute_fno_decision(_dhan(db, current_user.id), data.decision, data.correlation_id)
    except (DhanAPIError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
