from __future__ import annotations

from collections import defaultdict
from typing import Sequence


def _bucket(value: object) -> str:
    if value is None:
        return "UNKNOWN"
    text = str(value)
    if "T" in text:
        text = text.split("T", 1)[1]
    if " " in text:
        text = text.split(" ", 1)[-1]
    return text[:5] if len(text) >= 5 else text


def analyze_intraday_trades(trades: Sequence[dict]) -> dict:
    """Analyze completed trades without changing the strategy or backtest rules."""
    by_hour: dict[str, list[float]] = defaultdict(list)
    by_reason: dict[str, list[float]] = defaultdict(list)
    streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    current_loss_streak = 0
    current_win_streak = 0

    for trade in trades:
        pnl = float(trade.get("pnl", 0.0))
        by_reason[str(trade.get("reason", "UNKNOWN"))].append(pnl)
        bucket = _bucket(trade.get("entry_time"))
        by_hour[bucket].append(pnl)
        if pnl > 0:
            current_win_streak += 1
            current_loss_streak = 0
            max_win_streak = max(max_win_streak, current_win_streak)
        elif pnl < 0:
            current_loss_streak += 1
            current_win_streak = 0
            max_loss_streak = max(max_loss_streak, current_loss_streak)
        else:
            current_win_streak = current_loss_streak = 0

    def summarize(values: list[float]) -> dict:
        wins = [v for v in values if v > 0]
        losses = [v for v in values if v < 0]
        gross_loss = abs(sum(losses))
        return {
            "trades": len(values),
            "win_rate_percent": round(len(wins) / len(values) * 100, 2) if values else 0.0,
            "net_pnl": round(sum(values), 2),
            "expectancy": round(sum(values) / len(values), 4) if values else 0.0,
            "profit_factor": round(sum(wins) / gross_loss, 4) if gross_loss else None,
        }

    return {
        "trades": len(trades),
        "max_consecutive_wins": max_win_streak,
        "max_consecutive_losses": max_loss_streak,
        "by_entry_time": {key: summarize(values) for key, values in sorted(by_hour.items())},
        "by_exit_reason": {key: summarize(values) for key, values in sorted(by_reason.items())},
    }
