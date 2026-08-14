from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.broker_connection import BrokerConnection
from app.models.holding import Holding
from app.services.advanced_analytics_service import calculate_advanced_analytics
from app.services.market_service import MarketDataProviderError, get_history, get_quote
from app.services.signal_service import generate_signal
from app.services.technical_service import technical_snapshot
from app.services.watchlist_service import get_watchlist

SYMBOL_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,29}$")


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not SYMBOL_PATTERN.fullmatch(normalized):
        raise ValueError("Symbol must contain 1-30 letters, numbers, dots, underscores, or hyphens.")
    return normalized


def _history_rows(symbol: str, failures: list[dict[str, str]]) -> list[dict[str, float | None]]:
    try:
        history = get_history(symbol, range_="6mo", interval="1d")
    except MarketDataProviderError as exc:
        failures.append({"symbol": symbol, "error": str(exc)})
        return []
    return [
        {"close": float(row["close"]), "high": float(row["high"]), "low": float(row["low"]), "volume": float(row["volume"]) if row.get("volume") is not None else None}
        for row in history.data
        if row.get("close") is not None and row.get("high") is not None and row.get("low") is not None
    ]


def _stock_context(symbol: str, failures: list[dict[str, str]]) -> dict[str, Any]:
    rows = _history_rows(symbol, failures)
    try:
        quote = get_quote(symbol)
        current_price = float(quote.price)
    except MarketDataProviderError as exc:
        failures.append({"symbol": symbol, "error": str(exc)})
        current_price = None
    closes = [row["close"] for row in rows]
    highs = [row["high"] for row in rows]
    lows = [row["low"] for row in rows]
    volumes = [row["volume"] for row in rows]
    technical = technical_snapshot(closes, highs, lows, volumes if all(value is not None for value in volumes) else None)
    signal = generate_signal(symbol, closes, highs, lows, volumes if all(value is not None for value in volumes) else None)
    return {
        "symbol": symbol,
        "current_price": current_price if current_price is not None else technical["price"],
        "technical": technical,
        "technical_signal": signal,
    }


def build_stock_context(symbol: str) -> dict[str, Any]:
    normalized = normalize_symbol(symbol)
    failures: list[dict[str, str]] = []
    return {"analysis_type": "stock", "stock": _stock_context(normalized, failures), "market_data": {"failures": failures, "unavailable_symbols": sorted({item["symbol"] for item in failures})}}


def build_portfolio_context(db: Session, user_id: int) -> dict[str, Any]:
    holdings = db.query(Holding).filter(Holding.user_id == user_id).order_by(Holding.symbol).all()
    failures: list[dict[str, str]] = []
    quotes: dict[str, float] = {}
    histories: dict[str, list[float]] = {}
    technical_by_symbol: dict[str, dict[str, Any]] = {}
    for holding in holdings:
        symbol = normalize_symbol(holding.symbol)
        stock = _stock_context(symbol, failures)
        if stock["current_price"] is not None:
            quotes[symbol] = float(stock["current_price"])
        rows = _history_rows(symbol, failures)
        histories[symbol] = [float(row["close"]) for row in rows if row["close"] is not None]
        technical_by_symbol[symbol] = stock
    metrics = calculate_advanced_analytics(holdings, quotes, histories)
    values = {item["symbol"]: item for item in metrics["holdings"]}
    context_holdings = []
    for holding in holdings:
        symbol = normalize_symbol(holding.symbol)
        value = values.get(symbol)
        if value is None:
            continue
        current_value = value["current_value"]
        context_holdings.append({
            "symbol": symbol, "quantity": float(holding.quantity), "average_buy_price": float(holding.average_buy_price),
            "current_price": technical_by_symbol[symbol]["current_price"], "invested_value": value["invested"],
            "current_value": current_value, "pnl": value["pnl"], "pnl_percent": value["return_percent"],
            "weight_percent": current_value / metrics["current_value"] * 100 if metrics["current_value"] else 0.0,
            "technical": technical_by_symbol[symbol]["technical"], "technical_signal": technical_by_symbol[symbol]["technical_signal"],
        })
    brokers = [row.broker_name for row in db.query(BrokerConnection).filter(BrokerConnection.user_id == user_id).all()]
    return {
        "analysis_type": "portfolio",
        "portfolio": {"total_invested": metrics["total_invested"], "current_value": metrics["current_value"], "total_pnl": metrics["total_pnl"], "return_percent": metrics["return_percent"], "holdings_count": len(holdings), "concentration_percent": metrics["concentration_percent"], "diversification_score": metrics["diversification_score"], "volatility_percent": metrics["volatility_percent"], "maximum_drawdown_percent": metrics["maximum_drawdown_percent"], "risk_summary": metrics["risk_summary"]},
        "holdings": context_holdings,
        "market_data": {"failures": failures, "unavailable_symbols": sorted(set(metrics["unavailable_symbols"]) | {item["symbol"] for item in failures})},
        "brokers": {"connected_names": brokers},
    }


def build_watchlist_context(db: Session, user_id: int) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    stocks = [_stock_context(normalize_symbol(item.symbol), failures) for item in get_watchlist(db, user_id)]
    return {"analysis_type": "watchlist", "watchlist": stocks, "market_data": {"failures": failures, "unavailable_symbols": sorted({item["symbol"] for item in failures})}}
