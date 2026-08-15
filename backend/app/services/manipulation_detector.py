from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import mean, pstdev
from typing import Sequence


@dataclass(frozen=True)
class ManipulationSignal:
    name: str
    severity: str
    score: float
    explanation: str


def _zscore(value: float, values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    baseline = [float(x) for x in values if isfinite(float(x))]
    if not baseline:
        return 0.0
    average = mean(baseline)
    deviation = pstdev(baseline)
    if deviation == 0:
        # A perfectly stable baseline is itself useful information: any
        # meaningful increase above it is an anomaly even though a classical
        # z-score is undefined.
        return float("inf") if value > average else (float("-inf") if value < average else 0.0)
    return (value - average) / deviation


def detect_market_pressure(
    closes: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    volumes: Sequence[float],
) -> dict:
    """Detect unusual price/volume behavior as a defensive risk filter.

    This is not a claim that manipulation occurred. It flags patterns that can
    accompany liquidity shocks, promotional/pump-like behavior, forced exits,
    or other abnormal trading conditions. Confirmation requires exchange,
    delivery, order-book and corporate/news data.
    """
    n = min(len(closes), len(highs), len(lows), len(volumes))
    if n < 30:
        return {"risk_level": "INSUFFICIENT_DATA", "score": 0.0, "signals": []}

    closes = [float(x) for x in closes[-n:]]
    highs = [float(x) for x in highs[-n:]]
    lows = [float(x) for x in lows[-n:]]
    volumes = [float(x) for x in volumes[-n:]]

    signals: list[ManipulationSignal] = []
    returns = [
        (closes[i] / closes[i - 1] - 1.0) * 100.0
        for i in range(1, n)
        if closes[i - 1]
    ]
    volume_z = _zscore(volumes[-1], volumes[-21:-1])

    if volume_z >= 3.0 and abs(returns[-1]) >= 4.0:
        direction = "up" if returns[-1] > 0 else "down"
        signals.append(ManipulationSignal(
            "PRICE_VOLUME_SHOCK", "HIGH", 35.0,
            f"Unusually high volume coincided with a {abs(returns[-1]):.1f}% {direction} move."
        ))

    recent_high = max(highs[-21:-1])
    recent_low = min(lows[-21:-1])
    if closes[-1] > recent_high and volume_z >= 2.0:
        signals.append(ManipulationSignal(
            "BREAKOUT_VOLUME_ANOMALY", "MEDIUM", 20.0,
            "Price broke a recent high with unusually high volume; verify the move before treating it as a clean breakout."
        ))
    elif closes[-1] < recent_low and volume_z >= 2.0:
        signals.append(ManipulationSignal(
            "BREAKDOWN_VOLUME_ANOMALY", "MEDIUM", 20.0,
            "Price broke a recent low with unusually high volume; verify liquidity and news before acting."
        ))

    if len(returns) >= 5:
        five_day = (closes[-1] / closes[-6] - 1.0) * 100.0
        volume_ratio = volumes[-5] / (mean(volumes[-25:-5]) or 1.0)
        if abs(five_day) >= 12.0 and volume_ratio >= 2.0:
            signals.append(ManipulationSignal(
                "RAPID_MOVE", "MEDIUM", 20.0,
                f"The stock moved {five_day:.1f}% over five sessions while volume was elevated."
            ))

    ranges = [
        (highs[i] - lows[i]) / closes[i - 1] * 100.0
        for i in range(1, n) if closes[i - 1]
    ]
    if len(ranges) >= 21 and _zscore(ranges[-1], ranges[-21:-1]) >= 3.0:
        signals.append(ManipulationSignal(
            "RANGE_EXPANSION", "MEDIUM", 15.0,
            "The latest trading range is an extreme outlier versus recent sessions."
        ))

    score = min(100.0, sum(signal.score for signal in signals))
    if score >= 50:
        risk_level = "HIGH"
    elif score >= 25:
        risk_level = "ELEVATED"
    else:
        risk_level = "NORMAL"

    return {
        "risk_level": risk_level,
        "score": score,
        "signals": [signal.__dict__ for signal in signals],
        "disclaimer": "Anomaly detection is a defensive risk filter and does not establish market manipulation.",
    }
