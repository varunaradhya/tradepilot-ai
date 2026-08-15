from __future__ import annotations

from math import sqrt
from statistics import mean
from typing import Sequence


def summarize_equity_curve(equity_curve: Sequence[float], periods_per_year: int = 252) -> dict:
    values = [float(x) for x in equity_curve if x is not None]
    if not values:
        return {"observations": 0, "max_drawdown_percent": 0.0, "sharpe": None, "sortino": None}
    returns = [(values[i] / values[i - 1]) - 1 for i in range(1, len(values)) if values[i - 1] > 0]
    peak = values[0]
    max_drawdown = 0.0
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - value) / peak)
    if len(returns) < 2:
        return {"observations": len(values), "max_drawdown_percent": round(max_drawdown * 100, 2), "sharpe": None, "sortino": None}
    avg = mean(returns)
    variance = mean((r - avg) ** 2 for r in returns)
    std = sqrt(variance)
    downside = [min(0.0, r) for r in returns]
    downside_dev = sqrt(mean(x * x for x in downside))
    sharpe = (avg / std) * sqrt(periods_per_year) if std else None
    sortino = (avg / downside_dev) * sqrt(periods_per_year) if downside_dev else None
    return {
        "observations": len(values),
        "max_drawdown_percent": round(max_drawdown * 100, 2),
        "sharpe": round(sharpe, 4) if sharpe is not None else None,
        "sortino": round(sortino, 4) if sortino is not None else None,
    }


def summarize_trades(trades: Sequence[dict]) -> dict:
    pnls = [float(t.get("pnl", 0)) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    streak = worst_streak = 0
    for pnl in pnls:
        if pnl < 0:
            streak += 1
            worst_streak = max(worst_streak, streak)
        else:
            streak = 0
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "trades": len(pnls),
        "win_rate_percent": round(len(wins) / len(pnls) * 100, 2) if pnls else 0.0,
        "average_trade": round(mean(pnls), 2) if pnls else 0.0,
        "average_winner": round(mean(wins), 2) if wins else 0.0,
        "average_loser": round(mean(losses), 2) if losses else 0.0,
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else (float("inf") if gross_profit else None),
        "worst_losing_streak": worst_streak,
    }
