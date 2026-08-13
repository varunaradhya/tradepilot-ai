from __future__ import annotations

from datetime import datetime, timezone

from app.services.technical_service import technical_snapshot


def generate_signal(
    symbol: str,
    closes: list[float],
    highs: list[float] | None = None,
    lows: list[float] | None = None,
    volumes: list[float] | None = None,
) -> dict:
    snapshot = technical_snapshot(closes, highs, lows, volumes)

    if len(closes) < 50:
        return {"symbol": symbol.upper(), "signal": "HOLD", "confidence": 0.0, "reasons": ["Insufficient historical data for a technical signal."], "indicators": snapshot, "timestamp": datetime.now(timezone.utc), "data_status": "INSUFFICIENT_DATA"}

    score = 0
    reasons: list[str] = []

    rsi_value = snapshot["rsi"]
    trend = snapshot["trend"]
    momentum_value = snapshot["momentum_percent"]
    macd_value = snapshot["macd"]

    if trend == "BULLISH":
        score += 2
        reasons.append("EMA trend is bullish.")
    elif trend == "BEARISH":
        score -= 2
        reasons.append("EMA trend is bearish.")

    if rsi_value is not None:
        if rsi_value < 30:
            score += 2
            reasons.append("RSI indicates an oversold condition.")
        elif rsi_value > 70:
            score -= 2
            reasons.append("RSI indicates an overbought condition.")
        elif rsi_value >= 50:
            score += 1
            reasons.append("RSI has positive momentum bias.")
        else:
            score -= 1
            reasons.append("RSI has negative momentum bias.")

    if momentum_value is not None:
        if momentum_value > 0:
            score += 1
            reasons.append("Price momentum is positive.")
        elif momentum_value < 0:
            score -= 1
            reasons.append("Price momentum is negative.")

    if macd_value.get("histogram") is not None:
        if macd_value["histogram"] > 0:
            score += 1
            reasons.append("MACD histogram is positive.")
        elif macd_value["histogram"] < 0:
            score -= 1
            reasons.append("MACD histogram is negative.")

    if score >= 3:
        signal = "BUY"
    elif score <= -3:
        signal = "SELL"
    else:
        signal = "HOLD"

    confidence = min(95.0, max(50.0, 50.0 + abs(score) * 8.0))

    price = snapshot["price"]
    atr_value = snapshot["atr"]

    if price is not None and atr_value and atr_value > 0:
        if signal == "BUY":
            stop = price - 1.5 * atr_value
            target = price + 3.0 * atr_value
        elif signal == "SELL":
            stop = price + 1.5 * atr_value
            target = price - 3.0 * atr_value
        else:
            stop = price - 1.5 * atr_value
            target = price + 3.0 * atr_value

        risk = abs(price - stop)
        reward = abs(target - price)
        risk_reward = reward / risk if risk else None
    else:
        stop = target = risk_reward = None

    risk_level = (
        "HIGH" if rsi_value is not None and (rsi_value > 75 or rsi_value < 25)
        else "MEDIUM"
    )

    return {
        "symbol": symbol.upper(),
        "signal": signal,
        "confidence": confidence,
        "risk_level": risk_level,
        "entry_price": price,
        "target_price": target,
        "stop_loss": stop,
        "risk_reward": risk_reward,
        "reasons": reasons,
        "indicators": snapshot,
        "timestamp": datetime.now(timezone.utc),
        "data_status": "AVAILABLE",
    }
