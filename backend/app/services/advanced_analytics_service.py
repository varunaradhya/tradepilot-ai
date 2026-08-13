from __future__ import annotations

from math import sqrt
from statistics import pstdev
from typing import Iterable


def _returns(closes: list[float]) -> list[float]:
    return [((current - previous) / previous) for previous, current in zip(closes, closes[1:]) if previous]


def calculate_advanced_analytics(
    holdings: Iterable,
    quotes: dict[str, float],
    histories: dict[str, list[float]] | None = None,
) -> dict:
    results = []
    unavailable_symbols = []
    for holding in holdings:
        symbol = str(holding.symbol).upper()
        if symbol not in quotes:
            unavailable_symbols.append(symbol)
            continue
        quantity = float(holding.quantity)
        invested = quantity * float(holding.average_buy_price)
        value = quantity * float(quotes[symbol])
        pnl = value - invested
        results.append({"symbol": symbol, "invested": invested, "current_value": value, "pnl": pnl, "return_percent": pnl / invested * 100 if invested else 0.0})

    results.sort(key=lambda item: item["current_value"], reverse=True)
    total_invested = sum(item["invested"] for item in results)
    current_value = sum(item["current_value"] for item in results)
    concentration = results[0]["current_value"] / current_value * 100 if current_value and results else 0.0
    histories = histories or {}
    return_sets = [_returns(histories[symbol]) for symbol in quotes if len(histories.get(symbol, [])) >= 2]
    portfolio_returns = [sum(values) / len(values) for values in zip(*return_sets)] if return_sets else []
    volatility = pstdev(portfolio_returns) * sqrt(252) * 100 if len(portfolio_returns) >= 2 else None
    equity = 1.0
    peak = 1.0
    drawdowns = []
    for daily_return in portfolio_returns:
        equity *= 1 + daily_return
        peak = max(peak, equity)
        drawdowns.append((equity / peak - 1) * 100)
    max_drawdown = min(drawdowns) if drawdowns else None
    pnl = current_value - total_invested
    return {
        "total_invested": total_invested, "current_value": current_value, "total_pnl": pnl,
        "return_percent": pnl / total_invested * 100 if total_invested else 0.0,
        "concentration_percent": concentration, "top_holding": results[0]["symbol"] if results else None,
        "holdings": results, "diversification_score": max(0.0, 100.0 - concentration),
        "risk_summary": "NO_MARKET_DATA" if not results else ("HIGH_CONCENTRATION" if concentration > 50 else "DIVERSIFIED"),
        "volatility_percent": volatility, "maximum_drawdown_percent": max_drawdown,
        "unavailable_symbols": unavailable_symbols,
    }
