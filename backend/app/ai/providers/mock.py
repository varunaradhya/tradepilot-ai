from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.ai.base import AIProvider


class MockAIProvider(AIProvider):
    """Deterministic local provider for safe development and testing."""

    name = "mock"

    def analyze(self, context: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(context, dict) or not isinstance(context.get("analysis_type"), str):
            raise ValueError("A valid structured intelligence context is required.")

        analysis_type = context["analysis_type"]
        if analysis_type == "portfolio":
            return self._portfolio_analysis(context)
        if analysis_type == "stock":
            return self._stock_analysis(context)
        if analysis_type == "watchlist":
            return self._watchlist_analysis(context)
        raise ValueError("Unsupported intelligence analysis type.")

    def _portfolio_analysis(self, context: dict[str, Any]) -> dict[str, Any]:
        portfolio = context["portfolio"]
        holdings = context["holdings"]
        unavailable = context["market_data"]["unavailable_symbols"]
        reasons = [
            f"Calculated portfolio return is {portfolio['return_percent']:.2f}%.",
            f"Largest holding weight is {portfolio['concentration_percent']:.2f}%.",
        ]
        risks = []
        opportunities = []
        if not holdings:
            return self._response(
                "No holdings are available to analyse yet.", "NEUTRAL", 0,
                ["Observed fact: the portfolio is empty."],
                ["No portfolio diversification or risk assessment is possible without holdings."],
                [], [], "LIMITED",
            )
        signal = "HOLD"
        confidence = 55
        if portfolio["concentration_percent"] > 50:
            risks.append("Calculated concentration exceeds 50%; one position has an outsized effect on results.")
        else:
            opportunities.append("Calculated concentration is below 50%, indicating the portfolio is not dominated by one holding.")
        if portfolio["return_percent"] < 0:
            risks.append("Calculated total return is negative; review position-specific drivers before changing exposure.")
        else:
            opportunities.append("Calculated total return is positive; monitor whether the trend remains supported by technical data.")
        if unavailable:
            risks.append(f"Market data was unavailable for: {', '.join(unavailable)}.")
        data_quality = "PARTIAL" if unavailable else "AVAILABLE"
        return self._response(
            "Interpretation: portfolio positioning is best treated as a hold while concentration and market-data coverage are monitored.",
            signal, confidence, reasons, risks, opportunities,
            [holding["symbol"] for holding in holdings if holding["weight_percent"] >= 25], data_quality,
        )

    def _stock_analysis(self, context: dict[str, Any]) -> dict[str, Any]:
        stock = context["stock"]
        technical = stock["technical"]
        signal_data = stock["technical_signal"]
        if signal_data["data_status"] != "AVAILABLE":
            return self._response(
                f"Observed fact: insufficient historical data is available for {stock['symbol']}.", "NEUTRAL", 0,
                ["Calculated technical indicators are incomplete."],
                ["Any directional interpretation would be unreliable with insufficient history."], [],
                [stock["symbol"]], "INSUFFICIENT_DATA",
            )
        signal = signal_data["signal"]
        reasons = [f"Observed price is {stock['current_price']:.2f}."] + signal_data["reasons"]
        risks = ["Interpretation: technical signals can change quickly and do not account for news or fundamental events."]
        if technical.get("rsi") is not None and (technical["rsi"] > 70 or technical["rsi"] < 30):
            risks.append("Calculated RSI is at an extreme, which can increase reversal risk.")
        return self._response(
            f"Interpretation: deterministic technical evidence currently supports a {signal} posture for {stock['symbol']}, not an execution instruction.",
            signal, int(signal_data["confidence"]), reasons, risks,
            ["Monitor trend, momentum, and volume confirmation before acting on this informational view."],
            [stock["symbol"]], "AVAILABLE",
        )

    def _watchlist_analysis(self, context: dict[str, Any]) -> dict[str, Any]:
        stocks = context["watchlist"]
        if not stocks:
            return self._response(
                "No watchlist symbols are available to analyse.", "NEUTRAL", 0,
                ["Observed fact: the watchlist is empty."], [], [], [], "LIMITED",
            )
        available = [item for item in stocks if item["technical_signal"]["data_status"] == "AVAILABLE"]
        buy_items = [item for item in available if item["technical_signal"]["signal"] == "BUY"]
        sell_items = [item for item in available if item["technical_signal"]["signal"] == "SELL"]
        strongest = max(buy_items or available, key=lambda item: item["technical_signal"]["confidence"], default=None)
        highest_risk = max(sell_items or available, key=lambda item: item["technical_signal"]["confidence"], default=None)
        watch_items = [item["symbol"] for item in stocks if item not in available]
        reasons = [f"Observed fact: {len(stocks)} watchlist symbol(s) were requested."]
        if strongest:
            reasons.append(f"Calculated signal confidence is highest for {strongest['symbol']} among available data.")
        risks = [f"{highest_risk['symbol']} has the strongest negative technical posture." ] if highest_risk else ["Technical data is unavailable or insufficient for all watchlist symbols."]
        return self._response(
            "Interpretation: compare technical signals with your own research; this is not a trade recommendation.",
            "HOLD", 50 if available else 0, reasons, risks,
            [f"{strongest['symbol']} has the strongest available technical setup."] if strongest else [],
            watch_items, "AVAILABLE" if len(available) == len(stocks) else "PARTIAL",
        )

    def _response(self, summary: str, signal: str, confidence: int, reasons: list[str], risks: list[str], opportunities: list[str], watch_items: list[str], data_quality: str) -> dict[str, Any]:
        return {
            "summary": summary,
            "market_view": "Interpretation based only on supplied portfolio and technical data; market events and certainty are not inferred.",
            "signal": signal,
            "confidence": max(0, min(100, confidence)),
            "reasons": reasons,
            "risks": risks,
            "opportunities": opportunities,
            "watch_items": watch_items,
            "data_quality": data_quality,
            "generated_at": datetime.now(timezone.utc),
        }
