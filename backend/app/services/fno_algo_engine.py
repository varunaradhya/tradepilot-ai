from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Sequence

from app.services.fno_cost_service import FNOCostConfig, estimate_net_pnl
from app.services.fno_strategy import FNOConfig, select_option_contracts


@dataclass(frozen=True)
class DirectionResult:
    direction: str
    confidence: float
    reasons: tuple[str, ...]
    atr: float
    spot: float


def _num(value: Any, default: float = 0.0) -> float:
    try:
        value = float(value)
        return value if isfinite(value) else default
    except (TypeError, ValueError):
        return default


def _ema(values: Sequence[float], period: int) -> float | None:
    if len(values) < period or period <= 0:
        return None
    alpha = 2.0 / (period + 1.0)
    result = sum(float(x) for x in values[:period]) / period
    for value in values[period:]:
        result = alpha * float(value) + (1.0 - alpha) * result
    return result


def _rsi(values: Sequence[float], period: int = 14) -> float | None:
    if len(values) < period + 1:
        return None
    gains = []
    losses = []
    for previous, current in zip(values[-period - 1:-1], values[-period:]):
        change = float(current) - float(previous)
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    average_gain = sum(gains) / period
    average_loss = sum(losses) / period
    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0
    rs = average_gain / average_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14) -> float | None:
    if len(closes) < period + 1 or len(highs) != len(closes) or len(lows) != len(closes):
        return None
    trs = []
    for index in range(1, len(closes)):
        high = float(highs[index])
        low = float(lows[index])
        previous_close = float(closes[index - 1])
        trs.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
    return sum(trs[-period:]) / period


def infer_direction(bars: Sequence[dict[str, Any]], minimum_confidence: float = 65.0) -> DirectionResult:
    if len(bars) < 60:
        return DirectionResult("NO_TRADE", 0.0, ("INSUFFICIENT_COMPLETED_BARS",), 0.0, 0.0)
    closes = [_num(bar.get("close")) for bar in bars]
    highs = [_num(bar.get("high")) for bar in bars]
    lows = [_num(bar.get("low")) for bar in bars]
    volumes = [_num(bar.get("volume")) for bar in bars]
    if any(value <= 0 for value in closes + highs + lows):
        return DirectionResult("NO_TRADE", 0.0, ("INVALID_MARKET_DATA",), 0.0, 0.0)

    spot = closes[-1]
    fast = _ema(closes, 9)
    slow = _ema(closes, 21)
    rsi = _rsi(closes)
    atr = _atr(highs, lows, closes)
    if fast is None or slow is None or rsi is None or atr is None or atr <= 0:
        return DirectionResult("NO_TRADE", 0.0, ("INDICATOR_DATA_UNAVAILABLE",), atr or 0.0, spot)

    vwap_volume = sum(volumes[-30:])
    vwap = sum(c * v for c, v in zip(closes[-30:], volumes[-30:])) / vwap_volume if vwap_volume > 0 else spot
    recent_high = max(highs[-6:-1])
    recent_low = min(lows[-6:-1])
    opening_high = max(highs[:6])
    opening_low = min(lows[:6])
    average_volume = sum(volumes[-21:-1]) / 20.0
    current_volume = volumes[-1]

    bullish = 0.0
    bearish = 0.0
    bull_reasons: list[str] = []
    bear_reasons: list[str] = []

    if spot > fast > slow:
        bullish += 25; bull_reasons.append("EMA_TREND_UP")
    elif spot < fast < slow:
        bearish += 25; bear_reasons.append("EMA_TREND_DOWN")

    if spot > vwap:
        bullish += 15; bull_reasons.append("ABOVE_VWAP")
    elif spot < vwap:
        bearish += 15; bear_reasons.append("BELOW_VWAP")

    if spot > recent_high:
        bullish += 20; bull_reasons.append("SHORT_MOMENTUM_BREAKOUT")
    elif spot < recent_low:
        bearish += 20; bear_reasons.append("SHORT_MOMENTUM_BREAKDOWN")

    if spot > opening_high:
        bullish += 15; bull_reasons.append("OPENING_RANGE_BREAKOUT")
    elif spot < opening_low:
        bearish += 15; bear_reasons.append("OPENING_RANGE_BREAKDOWN")

    if 52.0 <= rsi <= 70.0:
        bullish += 15; bull_reasons.append("RSI_BULLISH_ZONE")
    elif 30.0 <= rsi <= 48.0:
        bearish += 15; bear_reasons.append("RSI_BEARISH_ZONE")

    if current_volume >= average_volume * 1.15:
        if spot >= fast:
            bullish += 10; bull_reasons.append("VOLUME_CONFIRMATION")
        else:
            bearish += 10; bear_reasons.append("VOLUME_CONFIRMATION")

    best = max(bullish, bearish)
    second = min(bullish, bearish)
    confidence = round(min(99.0, best + max(0.0, best - second) * 0.35), 2)
    if best < minimum_confidence or best - second < 15.0:
        return DirectionResult("NO_TRADE", confidence, ("DIRECTION_NOT_CONFIDENT",), atr, spot)
    if bullish > bearish:
        return DirectionResult("BULLISH", confidence, tuple(bull_reasons), atr, spot)
    return DirectionResult("BEARISH", confidence, tuple(bear_reasons), atr, spot)


def build_autonomous_option_decision(
    *,
    underlying: dict[str, Any],
    bars: Sequence[dict[str, Any]],
    option_chain: dict[str, Any],
    lot_size: int,
    config: FNOConfig = FNOConfig(),
) -> dict[str, Any]:
    direction = infer_direction(bars)
    base = {"underlying": underlying, "direction": direction.direction, "direction_confidence": direction.confidence, "direction_reasons": list(direction.reasons), "spot": direction.spot, "underlying_atr": direction.atr, "execution_mode": "PAPER_ONLY"}
    if direction.direction == "NO_TRADE":
        return {"decision": "NO_TRADE", "reason": "DIRECTION_GATE_FAILED", **base}
    if lot_size <= 0:
        return {"decision": "NO_TRADE", "reason": "INVALID_EXCHANGE_LOT_SIZE", **base}

    candidates = select_option_contracts(option_chain, direction.direction, config, limit=8)
    if not candidates:
        return {"decision": "NO_TRADE", "reason": "NO_OPTION_CONTRACT_PASSED_FILTERS", **base}

    best = candidates[0]
    entry = _num(best.get("ask")) or _num(best.get("last_price"))
    delta = abs(_num(best.get("delta")))
    if entry <= 0 or delta <= 0 or direction.atr <= 0:
        return {"decision": "NO_TRADE", "reason": "INVALID_OPTION_RISK_INPUT", "contract": best, **base}

    expected_premium_move = max(delta * direction.atr, entry * 0.08)
    risk_per_unit = max(expected_premium_move * 0.75, entry * 0.06)
    stop = entry - risk_per_unit
    target = entry + risk_per_unit * 2.0
    if stop <= 0 or stop >= entry:
        return {"decision": "NO_TRADE", "reason": "INVALID_DYNAMIC_STOP", "contract": best, **base}

    capital = _num(underlying.get("capital"))
    risk_budget = capital * config.risk_per_trade
    max_capital = capital * config.max_capital_percent
    cost_config = FNOCostConfig()

    # Size by the actual net loss at the stop, including the round-trip
    # trading costs. Brokerage is per order, so sizing must be done in whole
    # lots and rechecked after the lot rounding.
    quantity = (int(max_capital // entry) // lot_size) * lot_size
    while quantity > 0:
        net_stop_pnl, stop_costs = estimate_net_pnl(entry, stop, quantity, cost_config)
        risk = abs(net_stop_pnl)
        if risk <= risk_budget:
            break
        quantity -= lot_size

    lots = quantity // lot_size
    if quantity <= 0:
        return {"decision": "NO_TRADE", "reason": "RISK_BUDGET_TOO_SMALL_FOR_ONE_LOT", "contract": best, "lot_size": lot_size, "risk_budget": round(risk_budget, 2), **base}

    net_stop_pnl, stop_costs = estimate_net_pnl(entry, stop, quantity, cost_config)
    net_target_pnl, target_costs = estimate_net_pnl(entry, target, quantity, cost_config)
    risk = abs(net_stop_pnl)
    reward = max(0.0, net_target_pnl)
    risk_reward = reward / risk if risk > 0 else 0.0
    if risk_reward < 1.8:
        return {"decision": "NO_TRADE", "reason": "RISK_REWARD_TOO_LOW_AFTER_COSTS", "contract": best, "risk_reward": round(risk_reward, 2), "stop_costs": stop_costs, "target_costs": target_costs, **base}

    return {
        "decision": "QUALIFIED",
        **base,
        "contract": best,
        "entry": round(entry, 4),
        "stop": round(stop, 4),
        "target": round(target, 4),
        "quantity": quantity,
        "lots": lots,
        "lot_size": lot_size,
        "risk_budget": round(risk_budget, 2),
        "max_capital": round(max_capital, 2),
        "risk_amount": round(risk, 2),
        "reward_amount": round(reward, 2),
        "risk_reward": round(risk_reward, 2),
        "expected_premium_move": round(expected_premium_move, 4),
        "position_capital": round(entry * quantity, 2),
        "estimated_stop_costs": stop_costs,
        "estimated_target_costs": target_costs,
        "paper_only": True,
    }
