from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class LivePaperPosition:
    """A read-only market-data mark of an existing paper position."""

    symbol: str
    quantity: int
    entry_price: float
    stop_loss: float
    target: float
    trailing_stop: float | None = None
    entry_charges: float = 0.0


@dataclass(frozen=True)
class LivePaperMark:
    symbol: str
    ltp: float
    timestamp: int
    gross_pnl: float
    estimated_exit_charges: float
    net_pnl: float
    exit_reason: str | None
    stale: bool


def _validate_tick(symbol: str, ltp: float, timestamp: int) -> None:
    if not symbol.strip():
        raise ValueError("symbol is required")
    if ltp <= 0:
        raise ValueError("ltp must be positive")
    if timestamp <= 0:
        raise ValueError("timestamp must be positive")


def mark_paper_position(
    position: LivePaperPosition,
    ltp: float,
    timestamp: int,
    *,
    now: int | None = None,
    max_tick_age_seconds: int = 10,
) -> LivePaperMark:
    """Mark an open paper position using a broker-supplied LTP.

    This function is deliberately broker-neutral and never submits an order.
    A stale tick is returned as a mark but cannot trigger an exit.
    """
    _validate_tick(position.symbol, ltp, timestamp)
    if position.quantity <= 0 or position.entry_price <= 0:
        raise ValueError("invalid paper position")
    if now is None:
        now = int(datetime.now(timezone.utc).timestamp())
    age = max(0, now - timestamp)
    stale = age > max_tick_age_seconds

    gross = (ltp - position.entry_price) * position.quantity
    # Exit charges are supplied by the caller's existing charge model. This
    # bridge intentionally does not invent brokerage/tax rates.
    estimated_exit = 0.0
    net = gross - position.entry_charges - estimated_exit

    reason: str | None = None
    if not stale:
        if ltp <= position.stop_loss:
            reason = "STOP_LOSS"
        elif ltp >= position.target:
            reason = "TARGET"
        elif position.trailing_stop is not None and ltp <= position.trailing_stop:
            reason = "TRAILING_STOP"

    return LivePaperMark(
        symbol=position.symbol.upper(),
        ltp=float(ltp),
        timestamp=int(timestamp),
        gross_pnl=float(gross),
        estimated_exit_charges=float(estimated_exit),
        net_pnl=float(net),
        exit_reason=reason,
        stale=stale,
    )


def quote_payload_to_ltp(payload: dict[str, Any], symbol: str) -> float:
    """Extract an LTP from normalized Dhan quote payloads.

    Accepts either {symbol: {"last_price": ...}} or
    {symbol: {"ltp": ...}} to keep the bridge independent of transport shape.
    """
    item = payload.get(symbol) or payload.get(symbol.upper())
    if not isinstance(item, dict):
        raise ValueError(f"missing quote for {symbol}")
    raw = item.get("last_price", item.get("ltp"))
    if raw is None:
        raise ValueError(f"missing LTP for {symbol}")
    ltp = float(raw)
    if ltp <= 0:
        raise ValueError("LTP must be positive")
    return ltp
