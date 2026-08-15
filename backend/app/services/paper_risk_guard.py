from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class PaperRiskConfig:
    max_daily_loss: float = 1000.0
    max_daily_trades: int = 5
    max_consecutive_losses: int = 3
    max_open_positions: int = 1
    long_only: bool = True
    require_market_session: bool = True


@dataclass
class PaperRiskState:
    trading_date: date
    realized_pnl: float = 0.0
    trades_today: int = 0
    consecutive_losses: int = 0
    open_symbols: set[str] = field(default_factory=set)
    accepted_signal_ids: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str


def evaluate_paper_entry(
    *,
    side: str,
    symbol: str,
    signal_id: str,
    in_market_session: bool,
    state: PaperRiskState,
    config: PaperRiskConfig,
) -> RiskDecision:
    """Fail-closed gate for a new paper position.

    This guard intentionally does not place orders. It only decides whether a
    strategy signal is eligible to reach the paper execution layer.
    """
    if config.require_market_session and not in_market_session:
        return RiskDecision(False, "OUTSIDE_MARKET_SESSION")

    normalized_side = side.strip().upper()
    normalized_symbol = symbol.strip().upper()
    if config.long_only and normalized_side != "BUY":
        return RiskDecision(False, "LONG_ONLY")

    if not normalized_symbol:
        return RiskDecision(False, "INVALID_SYMBOL")
    if not signal_id.strip():
        return RiskDecision(False, "MISSING_SIGNAL_ID")
    if signal_id in state.accepted_signal_ids:
        return RiskDecision(False, "DUPLICATE_SIGNAL")

    if state.realized_pnl <= -abs(config.max_daily_loss):
        return RiskDecision(False, "DAILY_LOSS_LIMIT")
    if state.trades_today >= config.max_daily_trades:
        return RiskDecision(False, "DAILY_TRADE_LIMIT")
    if state.consecutive_losses >= config.max_consecutive_losses:
        return RiskDecision(False, "LOSS_STREAK_LIMIT")
    if normalized_symbol in state.open_symbols:
        return RiskDecision(False, "POSITION_ALREADY_OPEN")
    if len(state.open_symbols) >= config.max_open_positions:
        return RiskDecision(False, "OPEN_POSITION_LIMIT")

    return RiskDecision(True, "APPROVED")


def record_accepted_signal(state: PaperRiskState, signal_id: str) -> None:
    state.accepted_signal_ids.add(signal_id)


def record_closed_trade(state: PaperRiskState, pnl: float, symbol: str) -> None:
    state.realized_pnl += float(pnl)
    state.trades_today += 1
    state.open_symbols.discard(symbol.strip().upper())
    if pnl < 0:
        state.consecutive_losses += 1
    elif pnl > 0:
        state.consecutive_losses = 0


def open_position(state: PaperRiskState, symbol: str) -> None:
    state.open_symbols.add(symbol.strip().upper())
