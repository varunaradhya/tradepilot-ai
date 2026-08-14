from datetime import datetime
from unittest.mock import patch

import httpx
import pytest

from app.ai.analyst_service import _enforce_deterministic_authority
from app.ai.providers.external import ExternalAIProvider, ExternalProviderUnavailable
from app.ai.trading_intelligence import _score_stock, build_trading_view


def _stock(signal="BUY", status="AVAILABLE"):
    return {"symbol": "TCS", "current_price": 100.0, "technical": {"trend": "BULLISH", "rsi": 55.0, "momentum_percent": 3.0, "macd": {"histogram": 1.0}, "volume_trend": "ABOVE_AVERAGE", "sma_20": 95.0, "ema_20": 97.0, "ema_50": 90.0}, "technical_signal": {"signal": signal, "confidence": 74.0, "data_status": status}}


def test_external_provider_requires_configuration():
    with pytest.raises(ExternalProviderUnavailable):
        ExternalAIProvider(api_key="", model="", base_url="", timeout_seconds=1, max_retries=0, rate_limit=1)


def test_external_provider_validates_response_and_retries():
    calls = []

    class Response:
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": '{"summary":"test","signal":"BUY","confidence":60}'}}]}

    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs):
            calls.append(1)
            if len(calls) == 1: raise httpx.ReadTimeout("timeout")
            return Response()

    with patch("app.ai.providers.external.httpx.Client", Client):
        provider = ExternalAIProvider(api_key="key", model="model", base_url="https://example.test", timeout_seconds=1, max_retries=1, rate_limit=2)
        result = provider.analyze({"analysis_type": "stock"})
    assert len(calls) == 2
    assert result["signal"] == "BUY"
    assert result["confidence"] == 60


def test_external_provider_rejects_invalid_signal():
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": '{"summary":"test","signal":"EXECUTE","confidence":60}'}}]}
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs): return Response()
    with patch("app.ai.providers.external.httpx.Client", Client), pytest.raises(ExternalProviderUnavailable):
        ExternalAIProvider(api_key="key", model="model", base_url="https://example.test", timeout_seconds=1, max_retries=0, rate_limit=1).analyze({"analysis_type": "stock"})


def test_external_analysis_cannot_override_deterministic_signal():
    context = {"analysis_type": "stock", "stock": _stock("BUY")}
    analysis = _enforce_deterministic_authority(context, {"signal": "SELL", "confidence": 99, "limitations": []})
    assert analysis["signal"] == "BUY"
    assert analysis["confidence"] == 74
    unavailable = _enforce_deterministic_authority({"analysis_type": "stock", "stock": _stock(status="INSUFFICIENT_DATA")}, {"signal": "BUY", "confidence": 80, "limitations": []})
    assert unavailable["signal"] == "NEUTRAL"
    assert unavailable["confidence"] == 0


def test_opportunity_score_is_deterministic_and_signal_aware():
    first = _score_stock(_stock())
    second = _score_stock(_stock())
    assert first["score"] == second["score"]
    assert first["signal"] == "BUY"
    assert first["score"] > _score_stock(_stock("SELL"))["score"]


def test_trading_view_classifies_candidates():
    buy, hold, sell = _score_stock(_stock("BUY")), _score_stock(_stock("HOLD")), _score_stock(_stock("SELL"))
    with patch("app.ai.trading_intelligence.scan_opportunities", return_value={"opportunities": [buy, hold, sell], "unavailable_symbols": ["BAD"], "data_quality": "PARTIAL"}):
        view = build_trading_view(None, 1)
    assert [item["symbol"] for item in view["buy_candidates"]] == ["TCS"]
    assert len(view["sell_candidates"]) == 1
    assert view["unavailable_symbols"] == ["BAD"]
