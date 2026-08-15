from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Sequence


@dataclass(frozen=True)
class IntradaySignal:
    action: str
    confidence: float
    entry: float | None
    stop: float | None
    target: float | None
    risk_reward: float | None
    reasons: tuple[str, ...]


def _sma(values: Sequence[float], period: int) -> float:
    if len(values) < period:
        raise ValueError("INSUFFICIENT_DATA")
    return mean(values[-period:])


def generate_long_intraday_signal(
    closes: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    volumes: Sequence[float],
    *,
    opening_high: float | None = None,
    min_confidence: float = 65.0,
    stop_buffer: float = 0.002,
    reward_multiple: float = 2.0,
) -> IntradaySignal:
    """Deterministic long-first intraday signal; no order execution.

    Confidence is an evidence score, not a probability. It intentionally tops
    out below 100 so an unusually high threshold can still suppress a setup.
    """
    if min_confidence < 0 or min_confidence > 100:
        raise ValueError("INVALID_CONFIDENCE")
    if reward_multiple <= 0 or stop_buffer < 0:
        raise ValueError("INVALID_RISK_PARAMETERS")
    if not (len(closes) == len(highs) == len(lows) == len(volumes)):
        raise ValueError("SERIES_LENGTH_MISMATCH")
    if len(closes) < 20:
        raise ValueError("INSUFFICIENT_DATA")

    close = float(closes[-1])
    fast = _sma(closes, 9)
    slow = _sma(closes, 20)
    avg_volume = _sma(volumes, min(20, len(volumes)))

    score = 0.0
    reasons: list[str] = []
    if fast > slow:
        score += 25
        reasons.append("TREND_UP")
    if close > fast:
        score += 20
        reasons.append("PRICE_ABOVE_FAST_AVERAGE")
    if volumes[-1] >= avg_volume * 1.2:
        score += 20
        reasons.append("VOLUME_CONFIRMATION")
    if opening_high is not None and close > opening_high:
        score += 25
        reasons.append("OPENING_HIGH_BREAKOUT")

    if score < min_confidence:
        return IntradaySignal("NEUTRAL", round(score, 2), None, None, None, None, tuple(reasons))

    recent_low = min(float(x) for x in lows[-5:])
    stop = min(recent_low, close * (1.0 - stop_buffer))
    risk = close - stop
    if risk <= 0:
        return IntradaySignal("NEUTRAL", round(score, 2), None, None, None, None, tuple(reasons + ["INVALID_STOP"]))
    target = close + risk * reward_multiple
    rr = (target - close) / risk
    return IntradaySignal("BUY", round(min(score, 90.0), 2), close, round(stop, 4), round(target, 4), round(rr, 2), tuple(reasons))
