from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from app.services.technical_service import atr, ema, rsi, sma


@dataclass(frozen=True)
class StrategyConfig:
    fast_ema: int = 20
    slow_ema: int = 50
    breakout_period: int = 20
    rsi_min: float = 55.0
    rsi_max: float = 72.0
    volume_period: int = 20
    volume_multiplier: float = 1.2
    atr_period: int = 14
    stop_atr: float = 1.5
    target_atr: float = 3.0
    risk_per_trade: float = 0.005
    max_position_fraction: float = 0.20


@dataclass(frozen=True)
class Signal:
    action: str
    score: float
    entry: float | None
    stop: float | None
    target: float | None
    reason: tuple[str, ...]


def _valid(values: Sequence[float]) -> bool:
    return bool(values) and all(isfinite(float(x)) for x in values)


def generate_regime_momentum_signal(
    closes: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    volumes: Sequence[float] | None,
    config: StrategyConfig = StrategyConfig(),
) -> Signal:
    if len(closes) < max(config.slow_ema, config.breakout_period + 1, config.atr_period + 1):
        return Signal("NEUTRAL", 0.0, None, None, None, ("INSUFFICIENT_DATA",))
    if not (_valid(closes) and _valid(highs) and _valid(lows)):
        return Signal("NEUTRAL", 0.0, None, None, None, ("INVALID_PRICE_DATA",))

    price = float(closes[-1])
    fast = ema(closes, config.fast_ema)
    slow = ema(closes, config.slow_ema)
    current_rsi = rsi(closes)
    current_atr = atr(highs, lows, closes, config.atr_period)
    prior_high = max(float(x) for x in highs[-config.breakout_period - 1:-1])
    volume_ok = True
    if volumes is not None:
        if len(volumes) < config.volume_period + 1:
            return Signal("NEUTRAL", 0.0, None, None, None, ("INSUFFICIENT_VOLUME_DATA",))
        average_volume = sma(volumes[:-1], config.volume_period)
        volume_ok = average_volume is not None and float(volumes[-1]) >= average_volume * config.volume_multiplier

    if fast is None or slow is None or current_rsi is None or current_atr is None or current_atr <= 0:
        return Signal("NEUTRAL", 0.0, None, None, None, ("INSUFFICIENT_INDICATOR_DATA",))

    reasons: list[str] = []
    score = 0.0
    if price > fast > slow:
        score += 35
        reasons.append("UPTREND")
    else:
        return Signal("NEUTRAL", score, None, None, None, ("TREND_FILTER_FAILED",))

    if config.rsi_min <= current_rsi <= config.rsi_max:
        score += 20
        reasons.append("MOMENTUM_HEALTHY")
    else:
        return Signal("NEUTRAL", score, None, None, None, ("RSI_FILTER_FAILED",))

    if price > prior_high:
        score += 30
        reasons.append("BREAKOUT")
    else:
        return Signal("NEUTRAL", score, None, None, None, ("BREAKOUT_FILTER_FAILED",))

    if volume_ok:
        score += 15
        reasons.append("VOLUME_CONFIRMED")
    else:
        return Signal("NEUTRAL", score, None, None, None, ("VOLUME_FILTER_FAILED",))

    stop = price - config.stop_atr * current_atr
    target = price + config.target_atr * current_atr
    return Signal("BUY", score, price, stop, target, tuple(reasons))


def position_size(capital: float, entry: float, stop: float, config: StrategyConfig = StrategyConfig()) -> int:
    if capital <= 0 or entry <= 0 or stop <= 0 or stop >= entry:
        return 0
    risk_budget = capital * config.risk_per_trade
    risk_per_share = entry - stop
    by_risk = int(risk_budget // risk_per_share)
    by_capital = int((capital * config.max_position_fraction) // entry)
    return max(0, min(by_risk, by_capital))
