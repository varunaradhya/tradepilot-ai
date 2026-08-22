from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.brokers.dhan import DhanAPIError, DhanClient
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.paper_trade import PaperTrade
from app.services.broker_service import get_access_token, get_user_broker
from app.services.fno_algo_engine import build_autonomous_option_decision
from app.services.fno_execution import execute_fno_decision
from app.services.fno_strategy import FNOConfig, build_fno_decision, select_option_contracts
from app.services.fno_instrument_service import fno_instrument_master
from app.services.paper_trading_service import close_paper_trade, list_paper_trades, open_paper_trade, paper_trade_costs, update_paper_trade

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
class FNOAutoScanRequest(BaseModel):
    underlying_security_id: int = Field(gt=0)
    underlying_segment: str = Field(default="IDX_I", min_length=2, max_length=20)
    symbol: str = Field(min_length=1, max_length=30)
    capital: float = Field(default=100000.0, gt=0)
    interval: str = Field(default="5", pattern=r"^(1|5|15)$")
    expiry: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
class FNOExecuteRequest(BaseModel):
    decision: dict[str, Any]
    correlation_id: str = Field(default="tradepilot-fno", max_length=30)
class FNOPaperOpenRequest(BaseModel):
    decision: dict[str, Any]
    strategy_version: str = Field(default="V1", pattern="^(V1|V2)$")

def _dhan(db, user_id: int) -> DhanClient:
    c = get_user_broker(db, user_id, "DHAN")
    if c is None: raise HTTPException(status_code=404, detail="Dhan is not connected.")
    return DhanClient(c.client_id, get_access_token(c))

def _quote_from_response(response: dict[str, Any], security_id: str) -> dict[str, float] | None:
    data = response.get("data") if isinstance(response, dict) else None
    if not isinstance(data, dict): return None
    segment_data = data.get("NSE_FNO")
    if not isinstance(segment_data, dict): return None
    quote = segment_data.get(str(security_id))
    if not isinstance(quote, dict): return None
    def num(key: str) -> float | None:
        try:
            value = float(quote.get(key))
            return value if value > 0 else None
        except (TypeError, ValueError):
            return None
    bid = num("buy_price")
    ask = num("sell_price")
    if bid is None:
        depth = quote.get("depth")
        if isinstance(depth, dict):
            buys = depth.get("buy")
            sells = depth.get("sell")
            if isinstance(buys, list) and buys and isinstance(buys[0], dict):
                bid = num_from_depth(buys[0].get("price"))
            if isinstance(sells, list) and sells and isinstance(sells[0], dict):
                ask = num_from_depth(sells[0].get("price"))
    ltp = num("last_price")
    return {"bid": bid or ltp or 0.0, "ask": ask or ltp or 0.0, "ltp": ltp or 0.0}

def num_from_depth(value: Any) -> float | None:
    try:
        value = float(value)
        return value if value > 0 else None
    except (TypeError, ValueError):
        return None

def _ltp_from_response(response: dict[str, Any], security_id: str) -> float | None:
    data = response.get("data") if isinstance(response, dict) else None
    if not isinstance(data, dict): return None
    for segment in ("NSE_FNO", "NSE_EQ", "NSE_FNO_OPTIONS"):
        segment_data = data.get(segment)
        if isinstance(segment_data, dict):
            quote = segment_data.get(str(security_id))
            if quote is None and str(security_id).isdigit(): quote = segment_data.get(int(security_id))
            if isinstance(quote, dict):
                for key in ("last_price", "LTP", "ltp"):
                    try:
                        return float(quote[key]) if quote.get(key) is not None else None
                    except (TypeError, ValueError): pass
    quote = data.get(str(security_id))
    if isinstance(quote, dict):
        try: return float(quote.get("last_price", quote.get("ltp")))
        except (TypeError, ValueError): return None
    return None

def _expiry_dates(payload: Any) -> list[str]:
    values: list[str] = []
    def walk(value: Any) -> None:
        if isinstance(value, str) and len(value) >= 10:
            candidate = value[:10]
            try: datetime.strptime(candidate, "%Y-%m-%d"); values.append(candidate)
            except ValueError: pass
        elif isinstance(value, list):
            for item in value: walk(item)
        elif isinstance(value, dict):
            for item in value.values(): walk(item)
    walk(payload)
    return sorted(set(values))

def _historical_rows(client: DhanClient, security_id: int, segment: str, interval: str) -> list[dict[str, Any]]:
    """Fetch and normalize today's completed underlying candles."""
    ist = ZoneInfo("Asia/Kolkata")
    now = datetime.now(ist)
    session_start = now.replace(hour=9, minute=15, second=0, microsecond=0)
    if now < session_start: return []
    from_date = session_start.strftime("%Y-%m-%d %H:%M:%S")
    to_date = now.strftime("%Y-%m-%d %H:%M:%S")
    response = client.historical_intraday(str(security_id), segment, "INDEX", interval, from_date, to_date)
    data = response.get("data") if isinstance(response, dict) else None
    if not isinstance(data, dict): return []
    opens, highs, lows, closes = data.get("open") or [], data.get("high") or [], data.get("low") or [], data.get("close") or []
    volumes, timestamps = data.get("volume") or [0] * len(closes), data.get("timestamp") or data.get("time") or []
    bar_seconds = int(interval) * 60
    rows_by_timestamp: dict[int, dict[str, Any]] = {}
    for index, close in enumerate(closes):
        try:
            timestamp = float(timestamps[index])
            timestamp = timestamp / 1000.0 if timestamp > 10_000_000_000 else timestamp
            if timestamp + bar_seconds > now.timestamp(): continue
            row = {"open": float(opens[index]), "high": float(highs[index]), "low": float(lows[index]), "close": float(close), "volume": float(volumes[index]) if index < len(volumes) else 0.0, "timestamp": timestamp}
            if not all(value > 0 for value in (row["open"], row["high"], row["low"], row["close"])): continue
            if row["high"] < max(row["open"], row["close"]) or row["low"] > min(row["open"], row["close"]): continue
            rows_by_timestamp[int(timestamp)] = row
        except (IndexError, TypeError, ValueError): continue
    return [rows_by_timestamp[key] for key in sorted(rows_by_timestamp)]

@router.get("/underlyings")
def underlyings(q: str = Query(default="", max_length=50), current_user: User = Depends(get_current_user)):
    try: return [{"security_id":x.security_id,"exchange_segment":x.exchange_segment,"symbol":x.symbol,"name":x.name} for x in fno_instrument_master.search(q)]
    except Exception as exc: raise HTTPException(status_code=503, detail=f"Unable to load NSE F&O underlyings: {exc}") from exc

@router.post("/expiries")
def expiries(data: ExpiryRequest, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    try: return _dhan(db,current_user.id).option_expiries(data.underlying_security_id,data.underlying_segment)
    except DhanAPIError as exc: raise HTTPException(status_code=502, detail=str(exc)) from exc

@router.post("/chain")
def option_chain(data: OptionChainRequest, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    try: return _dhan(db,current_user.id).option_chain(data.underlying_security_id,data.underlying_segment,data.expiry)
    except DhanAPIError as exc: raise HTTPException(status_code=502, detail=str(exc)) from exc

@router.post("/auto-scan")
def autonomous_scan(data: FNOAutoScanRequest, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    client=_dhan(db,current_user.id)
    try:
        expiry_dates=_expiry_dates(client.option_expiries(data.underlying_security_id,data.underlying_segment))
        selected_expiry=data.expiry or (expiry_dates[0] if expiry_dates else None)
        if not selected_expiry: raise HTTPException(status_code=422, detail="No valid NSE option expiry is available.")
        raw_chain=client.option_chain(data.underlying_security_id,data.underlying_segment,selected_expiry)
        chain=raw_chain.get("data") if isinstance(raw_chain,dict) and isinstance(raw_chain.get("data"),dict) else raw_chain
        bars=_historical_rows(client,data.underlying_security_id,data.underlying_segment,data.interval)
        underlying={"symbol":data.symbol.strip().upper(),"security_id":data.underlying_security_id,"exchange_segment":data.underlying_segment,"expiry":selected_expiry,"capital":data.capital}
        preliminary=build_autonomous_option_decision(underlying=underlying,bars=bars,option_chain=chain,lot_size=1,config=FNOConfig())
        contract=preliminary.get("contract") or {}
        lot_size=fno_instrument_master.option_lot_size(data.symbol,selected_expiry,float(contract.get("strike",0)),str(contract.get("option_type","")),contract.get("security_id")) if contract else 0
        decision=build_autonomous_option_decision(underlying=underlying,bars=bars,option_chain=chain,lot_size=lot_size,config=FNOConfig())
        decision["completed_bars"] = len(bars)
        decision["data_status"] = "READY" if len(bars) >= 60 else "WAITING_FOR_COMPLETED_BARS"
        return {"mode":"PAPER_ONLY","symbol":data.symbol.strip().upper(),"interval":data.interval,"expiry":selected_expiry,"completed_bars":len(bars),"decision":decision}
    except DhanAPIError as exc: raise HTTPException(status_code=502, detail=str(exc)) from exc
    except HTTPException: raise
    except (TypeError,ValueError,RuntimeError) as exc: raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.post("/scan")
def scan(data: FNODecisionRequest, current_user: User = Depends(get_current_user)):
    try: cfg=FNOConfig(**{k:v for k,v in data.config.items() if k in FNOConfig.__dataclass_fields__})
    except (TypeError,ValueError) as exc: raise HTTPException(status_code=422, detail=str(exc)) from exc
    candidates=select_option_contracts(data.option_chain,data.direction,cfg)
    return {"candidates":candidates,"decision":build_fno_decision(data.underlying,data.direction,candidates,cfg),"mode":"PAPER_ONLY"}

@router.post("/paper/open")
def open_option_paper_trade(data: FNOPaperOpenRequest, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    decision=data.decision
    if decision.get("decision")!="QUALIFIED": raise HTTPException(status_code=422, detail="Only a QUALIFIED option decision can be paper traded.")
    contract=decision.get("contract") or {}; underlying=decision.get("underlying") or {}; security_id=contract.get("security_id"); quantity=int(decision.get("quantity") or 0); lot_size=int(decision.get("lot_size") or 0)
    if not security_id or quantity<=0 or lot_size<=0 or quantity%lot_size: raise HTTPException(status_code=422, detail="Option decision has invalid security ID, quantity, or lot size.")
    existing=db.query(PaperTrade).filter(PaperTrade.user_id==current_user.id,PaperTrade.status=="OPEN",PaperTrade.asset_type=="OPTION",PaperTrade.security_id==str(security_id)).first()
    if existing: raise HTTPException(status_code=409, detail="A paper position for this option contract is already open.")
    symbol=f"{underlying.get('symbol','OPTION')} {underlying.get('expiry','')} {contract.get('strike')} {contract.get('option_type')}".strip()
    try:
        trade=open_paper_trade(db,current_user.id,symbol=symbol[:30],quantity=quantity,entry_price=float(decision["entry"]),stop_price=float(decision["stop"]),target_price=float(decision["target"]),strategy_version=data.strategy_version,asset_type="OPTION",security_id=str(security_id),exchange_segment="NSE_FNO",underlying=str(underlying.get("symbol","")).upper(),expiry=underlying.get("expiry"),strike=float(contract.get("strike")) if contract.get("strike") is not None else None,option_type=contract.get("option_type"),lot_size=lot_size)
    except (KeyError,TypeError,ValueError) as exc: raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"mode":"PAPER_ONLY","position":{"id":trade.id,"symbol":trade.symbol,"underlying":trade.underlying,"expiry":trade.expiry,"strike":trade.strike,"option_type":trade.option_type,"security_id":trade.security_id,"quantity":trade.quantity,"entry_price":trade.entry_price,"stop_price":trade.stop_price,"target_price":trade.target_price,"pnl":trade.pnl,"status":trade.status}}

@router.get("/paper/positions")
def option_paper_positions(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    trades=[t for t in list_paper_trades(db,current_user.id,"OPEN") if t.asset_type=="OPTION"]
    if not trades: return {"mode":"PAPER_ONLY","market_connected":False,"positions":[]}
    client=_dhan(db,current_user.id); security_ids=[str(t.security_id) for t in trades if t.security_id]
    try: quotes=client.market_quote("NSE_FNO",security_ids)
    except DhanAPIError as exc: raise HTTPException(status_code=502, detail=str(exc)) from exc
    positions=[]
    for trade in trades:
        quote=_quote_from_response(quotes,str(trade.security_id))
        executable_price=quote["bid"] if quote and quote.get("bid",0)>0 else (quote.get("ltp",0) if quote else 0)
        if executable_price > 0:
            trade=update_paper_trade(db,trade,executable_price)
        costs=paper_trade_costs(trade,executable_price if executable_price > 0 else trade.entry_price)
        positions.append({"id":trade.id,"symbol":trade.symbol,"underlying":trade.underlying,"expiry":trade.expiry,"strike":trade.strike,"option_type":trade.option_type,"security_id":trade.security_id,"quantity":trade.quantity,"entry_price":trade.entry_price,"last_price":quote.get("ltp") if quote else None,"executable_bid":quote.get("bid") if quote else None,"ask":quote.get("ask") if quote else None,"stop_price":trade.stop_price,"target_price":trade.target_price,"pnl":trade.pnl,"estimated_round_trip_costs":costs,"status":trade.status,"reason":trade.reason})
    return {"mode":"PAPER_ONLY","market_connected":True,"positions":positions}

@router.post("/paper/positions/{trade_id}/close")
def close_option_paper_trade(trade_id:int,exit_price:float=Query(gt=0),current_user:User=Depends(get_current_user),db=Depends(get_db)):
    trade=db.query(PaperTrade).filter(PaperTrade.id==trade_id,PaperTrade.user_id==current_user.id,PaperTrade.asset_type=="OPTION").first()
    if trade is None: raise HTTPException(status_code=404,detail="Option paper position not found")
    try:
        costs=paper_trade_costs(trade,exit_price)
        trade=close_paper_trade(db,trade,exit_price,"MANUAL")
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    return {"mode":"PAPER_ONLY","position":{"id":trade.id,"status":trade.status,"exit_price":trade.exit_price,"pnl":trade.pnl,"estimated_round_trip_costs":costs,"reason":trade.reason}}

@router.post("/execute")
def execute(data:FNOExecuteRequest,current_user:User=Depends(get_current_user),db=Depends(get_db)):
    try: return execute_fno_decision(_dhan(db,current_user.id),data.decision,data.correlation_id)
    except (DhanAPIError,ValueError) as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc
