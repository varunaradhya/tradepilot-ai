from __future__ import annotations

from statistics import mean, pstdev
from typing import Sequence


def sma(values: Sequence[float], period: int) -> float | None:
    if period < 1 or len(values) < period:
        return None
    return mean(float(value) for value in values[-period:])


def ema(values: Sequence[float], period: int) -> float | None:
    if period < 1 or len(values) < period:
        return None
    alpha = 2.0 / (period + 1.0)
    result = mean(float(value) for value in values[:period])
    for value in values[period:]:
        result = alpha * float(value) + (1.0 - alpha) * result
    return result


def rsi(values: Sequence[float], period: int = 14) -> float | None:
    if len(values) < 2:
        return None

    if period < 1 or len(values) <= period:
        return None
    changes = [float(values[i]) - float(values[i - 1]) for i in range(1, len(values))]
    window = changes[-period:]

    gains = [x for x in window if x > 0]
    losses = [-x for x in window if x < 0]

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def macd(values: Sequence[float]) -> dict:
    if len(values) < 35:
        return {"macd": None, "signal": None, "histogram": None}
    lines = []
    for index in range(26, len(values) + 1):
        fast = ema(values[:index], 12)
        slow = ema(values[:index], 26)
        if fast is not None and slow is not None:
            lines.append(fast - slow)
    signal = ema(lines, 9)
    if signal is None:
        return {"macd": None, "signal": None, "histogram": None}
    line = lines[-1]
    return {
        "macd": line,
        "signal": signal,
        "histogram": line - signal if signal is not None else None,
    }


def bollinger(values: Sequence[float], period: int = 20, deviations: float = 2.0) -> dict:
    if period < 1 or len(values) < period:
        return {"middle": None, "upper": None, "lower": None}

    window = [float(x) for x in values[-period:]]
    middle = mean(window)
    deviation = pstdev(window) if len(window) > 1 else 0.0

    return {
        "middle": middle,
        "upper": middle + deviations * deviation,
        "lower": middle - deviations * deviation,
    }


def atr(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> float | None:
    if len(highs) < 2 or len(lows) < 2 or len(closes) < 2:
        return None

    count = min(len(highs), len(lows), len(closes))
    true_ranges = []

    for i in range(1, count):
        high = float(highs[i])
        low = float(lows[i])
        previous_close = float(closes[i - 1])
        true_ranges.append(
            max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )
        )

    if not true_ranges:
        return None

    return mean(true_ranges[-period:])


def momentum(values: Sequence[float], period: int = 10) -> float | None:
    if len(values) <= period:
        return None
    previous = float(values[-period - 1])
    current = float(values[-1])
    return ((current - previous) / previous * 100.0) if previous else 0.0


def technical_snapshot(
    closes: Sequence[float],
    highs: Sequence[float] | None = None,
    lows: Sequence[float] | None = None,
    volumes: Sequence[float] | None = None,
) -> dict:
    closes = [float(x) for x in closes]

    result = {
        "price": closes[-1] if closes else None,
        "sma_20": sma(closes, 20),
        "rsi": rsi(closes),
        "ema_20": ema(closes, 20),
        "ema_50": ema(closes, 50),
        "macd": macd(closes),
        "bollinger": bollinger(closes),
        "momentum_percent": momentum(closes),
        "atr": None,
        "volume_trend": None,
    }

    if highs is not None and lows is not None:
        result["atr"] = atr(highs, lows, closes)

    if volumes is not None and len(volumes) >= 20:
        average_volume = sma(volumes, 20)
        if average_volume and average_volume > 0:
            result["volume_trend"] = "ABOVE_AVERAGE" if float(volumes[-1]) > average_volume else "BELOW_AVERAGE"

    if len(closes) < 50:
        result["trend"] = "INSUFFICIENT_DATA"
    elif result["ema_20"] > result["ema_50"]:
        result["trend"] = "BULLISH"
    elif result["ema_20"] < result["ema_50"]:
        result["trend"] = "BEARISH"
    else:
        result["trend"] = "NEUTRAL"

    return result
