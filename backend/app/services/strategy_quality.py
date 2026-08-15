from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class SetupQuality:
    score: int
    regime: str
    trend_score: int
    momentum_score: int
    volume_score: int
    volatility_score: int


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> int:
    return int(round(max(low, min(high, value))))


def score_long_setup(
    closes: Sequence[float],
    fast_ema: float,
    slow_ema: float,
    volume_ratio: float,
    atr: float,
) -> SetupQuality:
    """Score a long setup without changing the entry rule itself.

    This is deliberately deterministic and explainable. It is a quality filter,
    not a price predictor or ML model.
    """
    if not closes or slow_ema <= 0 or closes[-1] <= 0:
        return SetupQuality(0, "UNKNOWN", 0, 0, 0, 0)

    lookback = min(5, len(closes) - 1)
    prior = closes[-1 - lookback] if lookback > 0 else closes[-1]
    # Regime slope must describe the observed price trend. Comparing the
    # current slow EMA to an older raw close mixes two different quantities and
    # can incorrectly label a clearly rising/falling series as sideways.
    slope_pct = ((closes[-1] / prior) - 1.0) * 100 if prior else 0.0

    trend = 45 if fast_ema > slow_ema else 0
    trend += _clamp(slope_pct * 500, 0, 35)
    trend = min(80, trend)

    momentum = 20 if closes[-1] > fast_ema else 0
    momentum += _clamp((closes[-1] / slow_ema - 1.0) * 500, 0, 25)
    momentum = min(45, momentum)

    volume = _clamp((volume_ratio - 1.0) * 50, 0, 30)

    atr_pct = (atr / closes[-1]) * 100
    if atr_pct < 0.15:
        volatility = 10
    elif atr_pct <= 4.0:
        volatility = 25
    else:
        volatility = 5

    score = _clamp(trend * 0.45 + momentum * 0.25 + volume * 0.20 + volatility * 0.10)

    if fast_ema > slow_ema and slope_pct > 0:
        regime = "TRENDING_UP"
    elif fast_ema < slow_ema and slope_pct < 0:
        regime = "TRENDING_DOWN"
    else:
        regime = "SIDEWAYS"

    return SetupQuality(
        score=score,
        regime=regime,
        trend_score=_clamp(trend),
        momentum_score=_clamp(momentum),
        volume_score=_clamp(volume),
        volatility_score=_clamp(volatility),
    )
