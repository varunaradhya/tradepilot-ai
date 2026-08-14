from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.context import build_portfolio_context, build_stock_context, build_watchlist_context
from app.ai.providers import MockAIProvider
from app.core.config import TRADEPILOT_AI_PROVIDER


def get_provider() -> AIProvider:
    if TRADEPILOT_AI_PROVIDER == "mock":
        return MockAIProvider()
    raise ValueError(f"AI provider '{TRADEPILOT_AI_PROVIDER}' is not configured.")


def analyze_portfolio(db: Session, user_id: int) -> dict[str, Any]:
    context = build_portfolio_context(db, user_id)
    return _analyze(context)


def analyze_stock(symbol: str) -> dict[str, Any]:
    return _analyze(build_stock_context(symbol))


def analyze_watchlist(db: Session, user_id: int) -> dict[str, Any]:
    return _analyze(build_watchlist_context(db, user_id))


def _analyze(context: dict[str, Any]) -> dict[str, Any]:
    provider = get_provider()
    return {"analysis": provider.analyze(context), "context_summary": _context_summary(context, provider.name)}


def _context_summary(context: dict[str, Any], provider: str) -> dict[str, Any]:
    summary = {"analysis_type": context["analysis_type"], "provider": provider, "market_data": context["market_data"]}
    if "portfolio" in context:
        summary["portfolio"] = context["portfolio"]
    if "stock" in context:
        summary["symbol"] = context["stock"]["symbol"]
    if "watchlist" in context:
        summary["symbols"] = [item["symbol"] for item in context["watchlist"]]
    return summary
