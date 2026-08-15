from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class MarketRegime:
    label: str
    trend_score: float
    volatility_percent: float
    momentum_percent: float
    confidence: float


def classify_market_regime(closes: list[float], lookback: int = 50) -> MarketRegime:
    values = [float(x) for x in closes if x is not None and float(x) > 0]
    if len(values) < max(lookback, 20):
        return MarketRegime("INSUFFICIENT_DATA", 0.0, 0.0, 0.0, 0.0)
    window = values[-lookback:]
    fast_n = min(20, len(window))
    slow = mean(window)
    fast = mean(window[-fast_n:])
    trend_score = (fast / slow - 1.0) * 100 if slow else 0.0
    momentum = (window[-1] / window[0] - 1.0) * 100 if window[0] else 0.0
    daily_returns = [(window[i] / window[i - 1] - 1.0) for i in range(1, len(window)) if window[i - 1] > 0]
    volatility = (mean(r * r for r in daily_returns) ** 0.5) * (252 ** 0.5) * 100 if daily_returns else 0.0
    if abs(trend_score) < 1.0 and abs(momentum) < 3.0:
        label = "SIDEWAYS"
    elif trend_score > 1.0 and momentum > 3.0:
        label = "BULL"
    elif trend_score < -1.0 and momentum < -3.0:
        label = "BEAR"
    else:
        label = "TRANSITION"
    confidence = min(100.0, abs(trend_score) * 20 + abs(momentum) * 5)
    return MarketRegime(label, round(trend_score, 4), round(volatility, 4), round(momentum, 4), round(confidence, 2))
