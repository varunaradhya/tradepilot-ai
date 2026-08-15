from __future__ import annotations

from typing import Sequence

from app.services.algo_strategy import StrategyConfig
from app.services.technical_service import atr, ema, rsi, sma


def diagnose_regime_momentum(
    closes: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    volumes: Sequence[float] | None,
    config: StrategyConfig = StrategyConfig(),
) -> dict:
    """Return explainable filter diagnostics without changing the trading signal."""
    required = max(config.slow_ema, config.breakout_period + 1, config.atr_period + 1)
    if len(closes) < required:
        return {"status": "INSUFFICIENT_DATA", "filters": {}}

    price = float(closes[-1])
    fast = ema(closes, config.fast_ema)
    slow = ema(closes, config.slow_ema)
    momentum_rsi = rsi(closes[:-1]) if len(closes) > 1 else None
    current_atr = atr(highs, lows, closes, config.atr_period)
    prior_high = max(float(x) for x in highs[-config.breakout_period - 1:-1])

    volume_ok = None
    volume_ratio = None
    if volumes is not None and len(volumes) >= config.volume_period + 1:
        average_volume = sma(volumes[:-1], config.volume_period)
        if average_volume and float(average_volume) > 0:
            volume_ratio = float(volumes[-1]) / float(average_volume)
            volume_ok = volume_ratio >= config.volume_multiplier

    filters = {
        "trend": {
            "passed": bool(fast is not None and slow is not None and price > fast > slow),
            "price": price,
            "fast_ema": fast,
            "slow_ema": slow,
        },
        "momentum": {
            "passed": bool(momentum_rsi is not None and config.rsi_min <= momentum_rsi <= config.rsi_max),
            "rsi": momentum_rsi,
            "minimum": config.rsi_min,
            "maximum": config.rsi_max,
        },
        "breakout": {
            "passed": price > prior_high,
            "price": price,
            "prior_high": prior_high,
        },
        "volume": {
            "passed": volume_ok,
            "ratio": volume_ratio,
            "minimum_ratio": config.volume_multiplier,
        },
        "volatility": {
            "passed": bool(current_atr is not None and current_atr > 0),
            "atr": current_atr,
        },
    }
    passed = [name for name, value in filters.items() if value["passed"] is True]
    failed = [name for name, value in filters.items() if value["passed"] is False]
    unknown = [name for name, value in filters.items() if value["passed"] is None]
    return {
        "status": "READY" if not failed and not unknown else "FILTERS_BLOCKED",
        "passed_filters": passed,
        "failed_filters": failed,
        "unknown_filters": unknown,
        "filters": filters,
    }
