from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.services.strategy_quality import score_long_setup


@dataclass(frozen=True)
class IntradayConfig:
    trade_direction: str = "LONG_ONLY"
    opening_bars: int = 3
    fast_period: int = 9
    slow_period: int = 20
    volume_period: int = 20
    min_volume_ratio: float = 1.5
    max_gap_percent: float = 3.0
    risk_per_trade: float = 0.005
    max_position_percent: float = 0.20
    atr_period: int = 14
    atr_stop_multiple: float = 1.5
    reward_multiple: float = 2.0
    min_quality_score: int = 55
    require_trending_regime: bool = True


def _validate_direction(config: IntradayConfig) -> None:
    if config.trade_direction not in {"LONG_ONLY", "LONG_SHORT"}:
        raise ValueError("trade_direction must be LONG_ONLY or LONG_SHORT")
    if not 0 <= config.min_quality_score <= 100:
        raise ValueError("min_quality_score must be between 0 and 100")


def _sma(values: Sequence[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _ema(values: Sequence[float], period: int) -> float | None:
    if len(values) < period:
        return None
    value = sum(values[:period]) / period
    alpha = 2.0 / (period + 1)
    for item in values[period:]:
        value = alpha * item + (1 - alpha) * value
    return value


def _atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int) -> float | None:
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    return sum(trs[-period:]) / period


def generate_intraday_signal(
    opens: Sequence[float], highs: Sequence[float], lows: Sequence[float], closes: Sequence[float],
    volumes: Sequence[float], opening_high: float | None = None, opening_low: float | None = None,
    config: IntradayConfig = IntradayConfig(),
) -> dict:
    _validate_direction(config)
    if not (len(opens) == len(highs) == len(lows) == len(closes) == len(volumes)):
        raise ValueError("OHLCV series must have equal lengths")
    minimum = max(config.slow_period, config.volume_period, config.atr_period + 1, config.opening_bars + 1)
    if len(closes) < minimum:
        return {"action": "NEUTRAL", "reason": "INSUFFICIENT_DATA", "trade_direction": config.trade_direction}
    close = float(closes[-1])
    fast = _ema(closes, config.fast_period)
    slow = _ema(closes, config.slow_period)
    avg_volume = _sma(volumes[:-1], config.volume_period)
    atr = _atr(highs, lows, closes, config.atr_period)
    if fast is None or slow is None or avg_volume in (None, 0) or atr in (None, 0):
        return {"action": "NEUTRAL", "reason": "INDICATORS_UNAVAILABLE", "trade_direction": config.trade_direction}
    if opening_high is None or opening_low is None:
        opening_high = max(highs[: config.opening_bars])
        opening_low = min(lows[: config.opening_bars])
    gap = abs(opens[0] / closes[0] - 1) * 100 if closes[0] else 0
    volume_ratio = volumes[-1] / avg_volume
    if gap > config.max_gap_percent:
        return {"action": "NEUTRAL", "reason": "EXTREME_GAP", "gap_percent": round(gap, 2), "trade_direction": config.trade_direction}
    if close <= opening_high or fast <= slow or volume_ratio < config.min_volume_ratio:
        return {"action": "NEUTRAL", "reason": "FILTERS_BLOCKED", "volume_ratio": round(volume_ratio, 2), "trade_direction": config.trade_direction}

    quality = score_long_setup(closes, fast, slow, volume_ratio, atr)
    if config.require_trending_regime and quality.regime != "TRENDING_UP":
        return {"action": "NEUTRAL", "reason": "REGIME_BLOCKED", "regime": quality.regime, "quality_score": quality.score, "trade_direction": config.trade_direction}
    if quality.score < config.min_quality_score:
        return {"action": "NEUTRAL", "reason": "QUALITY_SCORE_BLOCKED", "quality_score": quality.score, "regime": quality.regime, "trade_direction": config.trade_direction}

    entry = close
    stop = entry - config.atr_stop_multiple * atr
    target = entry + config.reward_multiple * (entry - stop)
    return {
        "action": "BUY",
        "trade_direction": "LONG_ONLY" if config.trade_direction == "LONG_ONLY" else config.trade_direction,
        "reason": "OPENING_RANGE_BREAKOUT",
        "entry": round(entry, 4),
        "stop": round(stop, 4),
        "target": round(target, 4),
        "volume_ratio": round(volume_ratio, 2),
        "atr": round(atr, 4),
        "risk_reward": config.reward_multiple,
        "quality_score": quality.score,
        "regime": quality.regime,
        "quality_components": {"trend": quality.trend_score, "momentum": quality.momentum_score, "volume": quality.volume_score, "volatility": quality.volatility_score},
    }
