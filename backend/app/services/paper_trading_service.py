from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.paper_trade import PaperTrade
from app.services.indian_costs import IndianEquityCostModel

_COST_MODEL = IndianEquityCostModel()

def _net_pnl(entry_price: float, exit_price: float, quantity: int) -> float:
    buy_value = entry_price * quantity
    sell_value = exit_price * quantity
    return round(sell_value - buy_value - _COST_MODEL.estimate_round_trip(buy_value, sell_value)["total"], 2)

def open_paper_trade(db: Session, user_id: int, *, symbol: str, quantity: int, entry_price: float, stop_price: float, target_price: float, strategy_version: str = "V1") -> PaperTrade:
    symbol = symbol.strip().upper()
    if not symbol or quantity <= 0 or entry_price <= 0 or stop_price <= 0 or target_price <= entry_price:
        raise ValueError("Invalid paper trade parameters")
    if stop_price >= entry_price:
        raise ValueError("Stop price must be below entry price for a long paper trade")
    if strategy_version not in {"V1", "V2"}:
        raise ValueError("strategy_version must be V1 or V2")
    trade = PaperTrade(user_id=user_id, symbol=symbol, side="BUY", status="OPEN", quantity=quantity, entry_price=entry_price, stop_price=stop_price, target_price=target_price, strategy_version=strategy_version)
    db.add(trade); db.commit(); db.refresh(trade); return trade

def update_paper_trade(db: Session, trade: PaperTrade, market_price: float, *, market_high: float | None = None, market_low: float | None = None) -> PaperTrade:
    if trade.status != "OPEN": return trade
    if market_price <= 0: raise ValueError("Market price must be positive")
    high = market_price if market_high is None else market_high
    low = market_price if market_low is None else market_low
    if high <= 0 or low <= 0 or low > high: raise ValueError("Invalid market high/low")
    if low <= trade.stop_price: return close_paper_trade(db, trade, trade.stop_price, "STOP")
    if high >= trade.target_price: return close_paper_trade(db, trade, trade.target_price, "TARGET")
    trade.pnl = _net_pnl(trade.entry_price, market_price, trade.quantity); db.commit(); db.refresh(trade); return trade

def close_paper_trade(db: Session, trade: PaperTrade, exit_price: float, reason: str = "MANUAL") -> PaperTrade:
    if trade.status != "OPEN": return trade
    if exit_price <= 0: raise ValueError("Exit price must be positive")
    trade.exit_price = exit_price; trade.pnl = _net_pnl(trade.entry_price, exit_price, trade.quantity); trade.reason = reason; trade.status = "CLOSED"; trade.closed_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(trade); return trade

def list_paper_trades(db: Session, user_id: int, status: str | None = None) -> list[PaperTrade]:
    query = db.query(PaperTrade).filter(PaperTrade.user_id == user_id)
    if status: query = query.filter(PaperTrade.status == status.upper())
    return query.order_by(PaperTrade.created_at.desc()).all()

def paper_summary(trades: list[PaperTrade]) -> dict:
    closed = [trade for trade in trades if trade.status == "CLOSED"]
    pnl = sum(float(trade.pnl) for trade in trades); realized = sum(float(trade.pnl) for trade in closed); wins = sum(1 for trade in closed if trade.pnl > 0)
    return {"trades": len(trades), "open_trades": len(trades) - len(closed), "closed_trades": len(closed), "pnl": round(pnl, 2), "realized_pnl": round(realized, 2), "win_rate_percent": round(wins / len(closed) * 100, 2) if closed else 0.0}
