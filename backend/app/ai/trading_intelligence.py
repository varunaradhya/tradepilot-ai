from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ai.context import _stock_context, normalize_symbol
from app.models.holding import Holding
from app.services.watchlist_service import get_watchlist


def scan_opportunities(db: Session, user_id: int) -> dict[str, Any]:
    symbols = {normalize_symbol(item.symbol) for item in get_watchlist(db, user_id)}
    symbols.update(normalize_symbol(item.symbol) for item in db.query(Holding).filter(Holding.user_id == user_id).all())
    failures: list[dict[str, str]] = []
    opportunities = []
    for symbol in sorted(symbols):
        stock = _stock_context(symbol, failures)
        if stock["technical_signal"]["data_status"] != "AVAILABLE":
            continue
        opportunities.append(_score_stock(stock))
    opportunities.sort(key=lambda item: (-item["score"], item["symbol"]))
    return {"opportunities": opportunities, "unavailable_symbols": sorted({item["symbol"] for item in failures}), "data_quality": "AVAILABLE" if not failures else "PARTIAL"}


def build_trading_view(db: Session, user_id: int) -> dict[str, Any]:
    scan = scan_opportunities(db, user_id)
    candidates = scan["opportunities"]
    by_signal = {signal: [item for item in candidates if item["signal"] == signal] for signal in ("BUY", "HOLD", "SELL")}
    strongest_momentum = max(candidates, key=lambda item: item["momentum_percent"] if item["momentum_percent"] is not None else float("-inf"), default=None)
    highest_risk = max(candidates, key=lambda item: item["risk_score"], default=None)
    return {
        "market_candidates": candidates,
        "buy_candidates": by_signal["BUY"],
        "hold_candidates": by_signal["HOLD"],
        "sell_candidates": by_signal["SELL"],
        "strongest_momentum": strongest_momentum,
        "highest_risk": highest_risk,
        "requires_attention": by_signal["SELL"] + [item for item in candidates if item["risk_score"] >= 60 and item["signal"] != "SELL"],
        "unavailable_symbols": scan["unavailable_symbols"],
        "data_quality": scan["data_quality"],
        "disclaimer": "Potential setups only; no outcome is certain and this endpoint never executes trades.",
    }


def _score_stock(stock: dict[str, Any]) -> dict[str, Any]:
    technical = stock["technical"]
    signal = stock["technical_signal"]
    score = 50
    reasons: list[str] = []
    risks: list[str] = []
    if technical["trend"] == "BULLISH":
        score += 15
        reasons.append("EMA trend is bullish.")
    elif technical["trend"] == "BEARISH":
        score -= 15
        risks.append("EMA trend is bearish.")
    rsi = technical.get("rsi")
    if rsi is not None:
        if 45 <= rsi <= 65:
            score += 8
            reasons.append("RSI is in a neutral-to-positive range.")
        elif rsi > 70:
            score -= 10
            risks.append("RSI is overbought.")
        elif rsi < 30:
            score += 4
            risks.append("RSI is oversold and can remain volatile.")
    momentum = technical.get("momentum_percent")
    if momentum is not None:
        if momentum > 0:
            score += 8
            reasons.append("Price momentum is positive.")
        elif momentum < 0:
            score -= 8
            risks.append("Price momentum is negative.")
    histogram = technical["macd"].get("histogram")
    if histogram is not None:
        if histogram > 0:
            score += 7
            reasons.append("MACD histogram is positive.")
        elif histogram < 0:
            score -= 7
            risks.append("MACD histogram is negative.")
    if technical.get("volume_trend") == "ABOVE_AVERAGE":
        score += 4
        reasons.append("Volume is above its recent average.")
    if signal["signal"] == "BUY":
        score += 8
        reasons.append("Deterministic signal is BUY.")
    elif signal["signal"] == "SELL":
        score -= 12
        risks.append("Deterministic signal is SELL.")
    score = max(0, min(100, score))
    risk_score = min(100, max(0, 100 - score + (15 if rsi is not None and (rsi < 30 or rsi > 70) else 0)))
    return {"symbol": stock["symbol"], "score": score, "signal": signal["signal"], "reasons": reasons or ["Technical inputs are mixed."], "risks": risks, "data_quality": "AVAILABLE", "price_context": {"current_price": stock["current_price"], "sma_20": technical.get("sma_20"), "ema_20": technical.get("ema_20"), "ema_50": technical.get("ema_50")}, "technical_summary": technical, "momentum_percent": momentum, "risk_score": risk_score}
