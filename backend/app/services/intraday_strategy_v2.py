from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.services.intraday_strategy import IntradayConfig, _atr, _ema, _sma
from app.services.strategy_quality import score_long_setup


@dataclass(frozen=True)
class IntradayV2Config(IntradayConfig):
    min_score: int = 4
    min_relative_strength: float = 0.002
    require_vwap: bool = True
    require_relative_strength: bool = True


@dataclass(frozen=True)
class IntradayV2AConfig(IntradayConfig):
    """V2-A: breakout-quality research layer using only symbol OHLCV data.

    This deliberately excludes market/sector inputs so it can be tested on the
    current clean symbol-partitioned dataset without inventing missing context.
    """

    min_quality_score: int = 55
    min_breakout_atr: float = 0.10
    max_breakout_atr: float = 1.50
    min_close_location: float = 0.65
    min_range_expansion: float = 1.10
    require_vwap: bool = True


def _vwap(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
) -> float | None:
    if not closes or len(closes) != len(volumes):
        return None
    total_volume = sum(volumes)
    if total_volume <= 0:
        return None
    return sum(
        ((h + l + c) / 3.0) * v
        for h, l, c, v in zip(highs, lows, closes, volumes)
    ) / total_volume


def _breakout_quality(
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    opening_high: float,
    atr: float,
    volume_period: int,
) -> dict:
    high = float(highs[-1])
    low = float(lows[-1])
    open_price = float(opens[-1])
    close = float(closes[-1])
    candle_range = high - low
    if candle_range <= 0 or atr <= 0:
        return {
            "breakout_distance_atr": 0.0,
            "close_location": 0.0,
            "range_expansion": 0.0,
            "breakout_quality": False,
        }

    close_location = (close - low) / candle_range
    breakout_distance_atr = (close - opening_high) / atr

    prior_ranges = [
        float(h) - float(l)
        for h, l in zip(highs[:-1], lows[:-1])
        if float(h) >= float(l)
    ]
    baseline_ranges = prior_ranges[-volume_period:]
    average_range = (
        sum(baseline_ranges) / len(baseline_ranges)
        if baseline_ranges
        else 0.0
    )
    range_expansion = candle_range / average_range if average_range > 0 else 0.0

    body_ratio = abs(close - open_price) / candle_range
    bullish_body = close >= open_price

    return {
        "breakout_distance_atr": round(breakout_distance_atr, 5),
        "close_location": round(close_location, 5),
        "range_expansion": round(range_expansion, 5),
        "body_ratio": round(body_ratio, 5),
        "bullish_body": bullish_body,
        "breakout_quality": True,
    }


def generate_intraday_v2_signal(
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    market_closes: Sequence[float] | None = None,
    sector_closes: Sequence[float] | None = None,
    opening_high: float | None = None,
    opening_low: float | None = None,
    config: IntradayV2Config = IntradayV2Config(),
) -> dict:
    if not (
        len(opens) == len(highs) == len(lows) == len(closes) == len(volumes)
    ):
        raise ValueError("OHLCV series must have equal lengths")
    minimum = max(
        config.slow_period,
        config.volume_period,
        config.atr_period + 1,
        config.opening_bars + 1,
    )
    if len(closes) < minimum:
        return {"action": "NEUTRAL", "reason": "INSUFFICIENT_DATA", "score": 0}

    fast, slow = _ema(closes, config.fast_period), _ema(
        closes, config.slow_period
    )
    avg_volume = _sma(volumes[:-1], config.volume_period)
    atr = _atr(highs, lows, closes, config.atr_period)
    vwap = _vwap(highs, lows, closes, volumes)
    if fast is None or slow is None or avg_volume in (None, 0) or atr in (None, 0) or vwap is None:
        return {"action": "NEUTRAL", "reason": "INDICATORS_UNAVAILABLE", "score": 0}

    if opening_high is None:
        opening_high = max(highs[: config.opening_bars])
    close = float(closes[-1])
    volume_ratio = volumes[-1] / avg_volume
    quality = score_long_setup(closes, fast, slow, volume_ratio, atr)
    checks = {
        "opening_breakout": close > opening_high,
        "trend": fast > slow,
        "volume": volume_ratio >= config.min_volume_ratio,
        "vwap": close > vwap,
    }
    if market_closes and len(market_closes) >= 2:
        relative_strength = (closes[-1] / closes[-2] - 1) - (
            market_closes[-1] / market_closes[-2] - 1
        )
        checks["relative_strength"] = relative_strength >= config.min_relative_strength
    else:
        relative_strength = None
        checks["relative_strength"] = not config.require_relative_strength
    checks["sector_strength"] = (
        (sector_closes[-1] / sector_closes[-2] - 1) > 0
        if sector_closes and len(sector_closes) >= 2
        else True
    )
    score = sum(checks.values())
    metadata = {
        "quality_score": quality.score,
        "regime": quality.regime,
        "quality_components": {
            "trend": quality.trend_score,
            "momentum": quality.momentum_score,
            "volume": quality.volume_score,
            "volatility": quality.volatility_score,
        },
    }
    if config.require_vwap and not checks["vwap"]:
        return {
            "action": "NEUTRAL",
            "reason": "VWAP_FILTER",
            "score": score,
            "checks": checks,
            **metadata,
        }
    if config.require_relative_strength and not checks["relative_strength"]:
        return {
            "action": "NEUTRAL",
            "reason": "RELATIVE_STRENGTH_FILTER",
            "score": score,
            "checks": checks,
            "relative_strength": relative_strength,
            **metadata,
        }
    if score < config.min_score:
        return {
            "action": "NEUTRAL",
            "reason": "SCORE_FILTER",
            "score": score,
            "checks": checks,
            **metadata,
        }
    entry = close
    stop = entry - config.atr_stop_multiple * atr
    target = entry + config.reward_multiple * (entry - stop)
    return {
        "action": "BUY",
        "reason": "ORB_V2_CONFIRMED",
        "score": score,
        "checks": checks,
        "entry": round(entry, 4),
        "stop": round(stop, 4),
        "target": round(target, 4),
        "atr": round(atr, 4),
        "vwap": round(vwap, 4),
        "volume_ratio": round(volume_ratio, 2),
        "relative_strength": (
            None if relative_strength is None else round(relative_strength, 5)
        ),
        **metadata,
    }


def generate_intraday_v2a_signal(
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    opening_high: float | None = None,
    opening_low: float | None = None,
    config: IntradayV2AConfig = IntradayV2AConfig(),
) -> dict:
    """Generate the isolated V2-A breakout-quality signal.

    V2-A intentionally uses no market/sector series. It adds confirmation to
    V1's ORB rather than changing the risk model, target, or execution model.
    """
    if not (
        len(opens) == len(highs) == len(lows) == len(closes) == len(volumes)
    ):
        raise ValueError("OHLCV series must have equal lengths")

    minimum = max(
        config.slow_period,
        config.volume_period + 1,
        config.atr_period + 1,
        config.opening_bars + 1,
    )
    if len(closes) < minimum:
        return {"action": "NEUTRAL", "reason": "INSUFFICIENT_DATA", "score": 0}

    fast = _ema(closes, config.fast_period)
    slow = _ema(closes, config.slow_period)
    avg_volume = _sma(volumes[:-1], config.volume_period)
    atr = _atr(highs, lows, closes, config.atr_period)
    vwap = _vwap(highs, lows, closes, volumes)
    if fast is None or slow is None or avg_volume in (None, 0) or atr in (None, 0) or vwap is None:
        return {"action": "NEUTRAL", "reason": "INDICATORS_UNAVAILABLE", "score": 0}

    if opening_high is None:
        opening_high = max(highs[: config.opening_bars])

    close = float(closes[-1])
    volume_ratio = float(volumes[-1]) / float(avg_volume)
    quality = score_long_setup(closes, fast, slow, volume_ratio, atr)
    breakout = _breakout_quality(
        opens, highs, lows, closes, volumes, float(opening_high), float(atr), config.volume_period
    )

    checks = {
        "opening_breakout": close > opening_high,
        "trend": fast > slow,
        "volume": volume_ratio >= config.min_volume_ratio,
        "quality_score": quality.score >= config.min_quality_score,
        "breakout_distance": (
            config.min_breakout_atr
            <= breakout["breakout_distance_atr"]
            <= config.max_breakout_atr
        ),
        "close_location": breakout["close_location"] >= config.min_close_location,
        "range_expansion": breakout["range_expansion"] >= config.min_range_expansion,
        "bullish_body": breakout["bullish_body"],
        "vwap": close > vwap,
        "trending_regime": quality.regime == "TRENDING_UP",
    }
    metadata = {
        "quality_score": quality.score,
        "regime": quality.regime,
        "quality_components": {
            "trend": quality.trend_score,
            "momentum": quality.momentum_score,
            "volume": quality.volume_score,
            "volatility": quality.volatility_score,
        },
        "breakout_quality": breakout,
        "vwap": round(vwap, 4),
        "volume_ratio": round(volume_ratio, 4),
    }

    if config.require_vwap and not checks["vwap"]:
        return {
            "action": "NEUTRAL",
            "reason": "VWAP_FILTER",
            "score": sum(checks.values()),
            "checks": checks,
            **metadata,
        }

    if not checks["opening_breakout"]:
        return {
            "action": "NEUTRAL",
            "reason": "OPENING_BREAKOUT_FILTER",
            "score": sum(checks.values()),
            "checks": checks,
            **metadata,
        }

    failed = [
        name for name, passed in checks.items()
        if name != "opening_breakout" and not passed
    ]
    if failed:
        return {
            "action": "NEUTRAL",
            "reason": "BREAKOUT_QUALITY_FILTER",
            "score": sum(checks.values()),
            "failed_checks": failed,
            "checks": checks,
            **metadata,
        }

    entry = close
    stop = entry - config.atr_stop_multiple * atr
    target = entry + config.reward_multiple * (entry - stop)
    return {
        "action": "BUY",
        "reason": "ORB_V2A_QUALITY_CONFIRMED",
        "score": sum(checks.values()),
        "checks": checks,
        "entry": round(entry, 4),
        "stop": round(stop, 4),
        "target": round(target, 4),
        "atr": round(atr, 4),
        **metadata,
    }
