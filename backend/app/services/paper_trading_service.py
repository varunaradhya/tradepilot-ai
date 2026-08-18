from datetime import datetime, timezone
import math

from sqlalchemy.orm import Session

from app.models.paper_trade import PaperTrade


def open_paper_trade(db: Session, user_id: int, *, symbol: str, quantity: int, entry_price: float, stop_price: float, target_price: float, strategy_version: str = "V1") -> PaperTrade:
    symbol = symbol.strip().upper()
    values = (float(quantity), float(entry_price), float(stop_price), float(target_price))
    if not symbol or any(not math.isfinite(value) for value in values) or quantity <= 0 or entry_price <= 0 or stop_price <= 0 or target_price <= entry_price:
        raise ValueError("Invalid paper trade parameters")
    if stop_price >= entry_price:
        raise ValueError("Stop price must be below entry price for a long paper trade")
    if strategy_version not in {"V1", "V2"}:
        raise ValueError("strategy_version must be V1 or V2")
    trade = PaperTrade(user_id=user_id, symbol=symbol, side="BUY", status="OPEN", quantity=quantity, entry_price=entry_price, stop_price=stop_price, target_price=target_price, strategy_version=strategy_version)
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


def update_paper_trade(db: Session, trade: PaperTrade, market_price: float, *, market_high: float | None = None, market_low: float | None = None) -> PaperTrade:
    if trade.status != "OPEN":
        return trade
    if not math.isfinite(market_price) or market_price <= 0:
        raise ValueError("Market price must be positive and finite")
    high = market_price if market_high is None else market_high
    low = market_price if market_low is None else market_low
    if not math.isfinite(high) or not math.isfinite(low) or high <= 0 or low <= 0 or low > high:
        raise ValueError("Invalid market range")
    if low <= trade.stop_price:
        return close_paper_trade(db, trade, trade.stop_price, "STOP")
    if high >= trade.target_price:
        return close_paper_trade(db, trade, trade.target_price, "TARGET")
    trade.pnl = (market_price - trade.entry_price) * trade.quantity
    db.commit()
    db.refresh(trade)
    return trade


def close_paper_trade(db: Session, trade: PaperTrade, exit_price: float, reason: str = "MANUAL") -> PaperTrade:
    if trade.status != "OPEN":
        return trade
    if not math.isfinite(exit_price) or exit_price <= 0:
        raise ValueError("Exit price must be positive and finite")
    reason = reason.strip().upper()
    if not reason:
        raise ValueError("Exit reason is required")
    trade.exit_price = exit_price
    trade.pnl = (exit_price - trade.entry_price) * trade.quantity
    trade.reason = reason
    trade.status = "CLOSED"
    trade.closed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(trade)
    return trade


def list_paper_trades(db: Session, user_id: int, status: str | None = None) -> list[PaperTrade]:
    query = db.query(PaperTrade).filter(PaperTrade.user_id == user_id)
    if status:
        query = query.filter(PaperTrade.status == status.upper())
    return query.order_by(PaperTrade.created_at.desc()).all()


def paper_summary(trades: list[PaperTrade]) -> dict:
    closed = [trade for trade in trades if trade.status == "CLOSED"]
    pnl = sum(float(trade.pnl) for trade in trades)
    realized = sum(float(trade.pnl) for trade in closed)
    wins = sum(1 for trade in closed if trade.pnl > 0)
    return {"trades": len(trades), "open_trades": len(trades) - len(closed), "closed_trades": len(closed), "pnl": round(pnl, 2), "realized_pnl": round(realized, 2), "win_rate_percent": round(wins / len(closed) * 100, 2) if closed else 0.0}
