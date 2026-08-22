from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Sequence


@dataclass(frozen=True)
class QualificationConfig:
    min_trades: int = 30
    min_profit_factor: float = 1.20
    max_drawdown_percent: float = 20.0
    min_expectancy: float = 0.0
    min_oos_trades: int = 10


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        value = float(value)
        return value if isfinite(value) else default
    except (TypeError, ValueError):
        return default


def _metrics(trades: Sequence[dict[str, Any]]) -> dict[str, float]:
    pnls = [_finite(t.get("pnl")) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    equity = [0.0]
    running = 0.0
    peak = 0.0
    max_dd = 0.0
    for pnl in pnls:
        running += pnl
        equity.append(running)
        peak = max(peak, running)
        if peak > 0:
            max_dd = max(max_dd, (peak - running) / peak * 100.0)
    return {
        "trades": float(len(pnls)),
        "win_rate_percent": (len(wins) / len(pnls) * 100.0) if pnls else 0.0,
        "profit_factor": (gross_profit / gross_loss) if gross_loss else (float("inf") if gross_profit else 0.0),
        "expectancy": (sum(pnls) / len(pnls)) if pnls else 0.0,
        "max_drawdown_percent": max_dd,
    }


def qualify_walk_forward(
    *,
    in_sample_trades: Sequence[dict[str, Any]],
    out_of_sample_trades: Sequence[dict[str, Any]],
    config: QualificationConfig = QualificationConfig(),
) -> dict[str, Any]:
    """Apply deterministic qualification gates without tuning strategy parameters.

    The function deliberately does not optimize anything. It only evaluates
    supplied, already-frozen trade results. This keeps the qualification stage
    separate from strategy development and prevents validation data from being
    used to tune the strategy.
    """
    ins = _metrics(in_sample_trades)
    oos = _metrics(out_of_sample_trades)
    gates = {
        "in_sample_min_trades": ins["trades"] >= config.min_trades,
        "in_sample_profit_factor": ins["profit_factor"] >= config.min_profit_factor,
        "in_sample_expectancy": ins["expectancy"] > config.min_expectancy,
        "in_sample_drawdown": ins["max_drawdown_percent"] <= config.max_drawdown_percent,
        "oos_min_trades": oos["trades"] >= config.min_oos_trades,
        "oos_profit_factor": oos["profit_factor"] >= config.min_profit_factor,
        "oos_expectancy": oos["expectancy"] > config.min_expectancy,
        "oos_drawdown": oos["max_drawdown_percent"] <= config.max_drawdown_percent,
    }
    return {
        "qualified": all(gates.values()),
        "gates": gates,
        "in_sample": ins,
        "out_of_sample": oos,
        "config": {
            "min_trades": config.min_trades,
            "min_profit_factor": config.min_profit_factor,
            "max_drawdown_percent": config.max_drawdown_percent,
            "min_expectancy": config.min_expectancy,
            "min_oos_trades": config.min_oos_trades,
        },
    }
