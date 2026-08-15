from __future__ import annotations

from dataclasses import dataclass, asdict
from math import inf
from typing import Iterable, Sequence


@dataclass(frozen=True)
class QualityThresholdMetrics:
    threshold: int
    trades: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float | None
    net_pnl: float
    average_pnl: float
    max_drawdown: float


def _max_drawdown(pnls: Sequence[float]) -> float:
    equity = peak = 0.0
    drawdown = 0.0
    for pnl in pnls:
        equity += float(pnl)
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown


def evaluate_quality_thresholds(
    quality_scores: Sequence[float],
    realized_pnls: Sequence[float],
    thresholds: Iterable[int] = (0, 50, 60, 70, 80),
) -> tuple[QualityThresholdMetrics, ...]:
    """Describe outcomes at fixed quality thresholds; never optimize them."""
    if len(quality_scores) != len(realized_pnls):
        raise ValueError("quality_scores and realized_pnls must have equal length")

    normalized = tuple(sorted(set(int(t) for t in thresholds)))
    if any(t < 0 or t > 100 for t in normalized):
        raise ValueError("quality thresholds must be between 0 and 100")

    results: list[QualityThresholdMetrics] = []
    for threshold in normalized:
        pnls = [
            float(pnl)
            for score, pnl in zip(quality_scores, realized_pnls)
            if float(score) >= threshold
        ]
        wins = sum(pnl > 0 for pnl in pnls)
        losses = sum(pnl < 0 for pnl in pnls)
        gross_profit = sum(pnl for pnl in pnls if pnl > 0)
        gross_loss = -sum(pnl for pnl in pnls if pnl < 0)
        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else (inf if gross_profit > 0 else None)
        )
        results.append(
            QualityThresholdMetrics(
                threshold=threshold,
                trades=len(pnls),
                wins=wins,
                losses=losses,
                win_rate=(wins / len(pnls) * 100) if pnls else 0.0,
                profit_factor=profit_factor,
                net_pnl=sum(pnls),
                average_pnl=(sum(pnls) / len(pnls)) if pnls else 0.0,
                max_drawdown=_max_drawdown(pnls),
            )
        )
    return tuple(results)


def compare_train_oos_quality_thresholds(
    train_scores: Sequence[float],
    train_pnls: Sequence[float],
    oos_scores: Sequence[float],
    oos_pnls: Sequence[float],
    thresholds: Iterable[int] = (0, 50, 60, 70, 80),
) -> dict[str, object]:
    """Return fixed-threshold train/OOS evidence without selecting a winner."""
    train = evaluate_quality_thresholds(train_scores, train_pnls, thresholds)
    oos = evaluate_quality_thresholds(oos_scores, oos_pnls, thresholds)
    return {
        "thresholds": [item.threshold for item in train],
        "train": [asdict(item) for item in train],
        "oos": [asdict(item) for item in oos],
        "selection_policy": "descriptive_only_no_threshold_optimization",
    }
