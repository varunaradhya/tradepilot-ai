from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from math import inf
from typing import Iterable


@dataclass(frozen=True)
class RegimeMetrics:
    regime: str
    trades: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float | None
    net_pnl: float
    average_pnl: float


def summarize_regimes(
    regimes: Iterable[str],
    realized_pnls: Iterable[float],
) -> tuple[RegimeMetrics, ...]:
    """Aggregate realized trade outcomes by pre-computed market regime."""
    regimes = tuple(str(item) for item in regimes)
    pnls = tuple(float(item) for item in realized_pnls)
    if len(regimes) != len(pnls):
        raise ValueError("regimes and realized_pnls must have equal length")

    grouped: dict[str, list[float]] = defaultdict(list)
    for regime, pnl in zip(regimes, pnls):
        grouped[regime].append(pnl)

    result: list[RegimeMetrics] = []
    for regime in sorted(grouped):
        values = grouped[regime]
        wins = sum(value > 0 for value in values)
        losses = sum(value < 0 for value in values)
        gross_profit = sum(value for value in values if value > 0)
        gross_loss = -sum(value for value in values if value < 0)
        result.append(
            RegimeMetrics(
                regime=regime,
                trades=len(values),
                wins=wins,
                losses=losses,
                win_rate=(wins / len(values) * 100) if values else 0.0,
                profit_factor=(
                    gross_profit / gross_loss
                    if gross_loss > 0
                    else (inf if gross_profit > 0 else None)
                ),
                net_pnl=sum(values),
                average_pnl=sum(values) / len(values),
            )
        )
    return tuple(result)


def regime_report(regimes: Iterable[str], realized_pnls: Iterable[float]) -> dict[str, object]:
    """Return a stable regime scorecard for research/UI consumption."""
    metrics = summarize_regimes(regimes, realized_pnls)
    return {
        "regimes": [asdict(item) for item in metrics],
        "selection_policy": "descriptive_only_no_regime_optimization",
    }
