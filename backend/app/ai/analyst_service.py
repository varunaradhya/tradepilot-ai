from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai import cache
from app.ai.context import build_portfolio_context, build_stock_context, build_watchlist_context
from app.ai.providers import ExternalAIProvider, ExternalProviderUnavailable, MockAIProvider
from app.core.config import TRADEPILOT_AI_API_KEY, TRADEPILOT_AI_BASE_URL, TRADEPILOT_AI_CACHE_TTL_SECONDS, TRADEPILOT_AI_MAX_RETRIES, TRADEPILOT_AI_MODEL, TRADEPILOT_AI_PROVIDER, TRADEPILOT_AI_RATE_LIMIT, TRADEPILOT_AI_TIMEOUT_SECONDS
from app.services.ai_history_service import store_analysis


def get_provider() -> AIProvider:
    if TRADEPILOT_AI_PROVIDER == "mock":
        return MockAIProvider()
    if TRADEPILOT_AI_PROVIDER == "external":
        return ExternalAIProvider(api_key=TRADEPILOT_AI_API_KEY, model=TRADEPILOT_AI_MODEL, base_url=TRADEPILOT_AI_BASE_URL, timeout_seconds=TRADEPILOT_AI_TIMEOUT_SECONDS, max_retries=TRADEPILOT_AI_MAX_RETRIES, rate_limit=TRADEPILOT_AI_RATE_LIMIT)
    raise ValueError(f"AI provider '{TRADEPILOT_AI_PROVIDER}' is not supported.")


def analyze_portfolio(db: Session, user_id: int) -> dict[str, Any]:
    context = build_portfolio_context(db, user_id)
    return _analyze(context, db, user_id, None)


def analyze_stock(db: Session, user_id: int, symbol: str) -> dict[str, Any]:
    return _analyze(build_stock_context(symbol), db, user_id, symbol)


def analyze_watchlist(db: Session, user_id: int) -> dict[str, Any]:
    return _analyze(build_watchlist_context(db, user_id), db, user_id, None)


def _analyze(context: dict[str, Any], db: Session, user_id: int, symbol: str | None) -> dict[str, Any]:
    cached = cache.get(user_id, context["analysis_type"], symbol, TRADEPILOT_AI_CACHE_TTL_SECONDS)
    if cached:
        cached["context_summary"] = {**cached["context_summary"], "cached": True}
        return cached
    try:
        provider = get_provider()
        analysis = provider.analyze(context)
        provider_name = provider.name
    except ExternalProviderUnavailable:
        analysis = MockAIProvider().analyze(context)
        provider_name = "mock_fallback"
    analysis = _enforce_deterministic_authority(context, analysis)
    result = {"analysis": analysis, "context_summary": _context_summary(context, provider_name)}
    store_analysis(db, user_id, context["analysis_type"], symbol, provider_name, analysis)
    cache.set(user_id, context["analysis_type"], symbol, TRADEPILOT_AI_CACHE_TTL_SECONDS, result)
    return result


def _enforce_deterministic_authority(context: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    if context["analysis_type"] != "stock":
        return analysis
    deterministic = context["stock"]["technical_signal"]
    if deterministic["data_status"] != "AVAILABLE":
        analysis["signal"] = "NEUTRAL"
        analysis["confidence"] = 0
        analysis["limitations"] = analysis.get("limitations", []) + ["Insufficient historical data prevents a directional deterministic signal."]
        return analysis
    analysis["signal"] = deterministic["signal"]
    analysis["confidence"] = int(deterministic["confidence"])
    return analysis


def _context_summary(context: dict[str, Any], provider: str) -> dict[str, Any]:
    summary = {"analysis_type": context["analysis_type"], "provider": provider, "market_data": context["market_data"]}
    if "portfolio" in context:
        summary["portfolio"] = context["portfolio"]
    if "stock" in context:
        summary["symbol"] = context["stock"]["symbol"]
        summary["stock"] = {
            "current_price": context["stock"]["current_price"],
            "technical_summary": context["stock"]["technical"],
            "support": None,
            "resistance": None,
        }
    if "watchlist" in context:
        summary["symbols"] = [item["symbol"] for item in context["watchlist"]]
    return summary
