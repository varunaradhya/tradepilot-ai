import pytest

from app.brokers.adapters import AngelOneAdapter, GrowwAdapter, UnsupportedBrokerAdapter
from app.brokers.capabilities import capabilities_for
from app.brokers.errors import BrokerErrorCode, normalize_broker_error
from app.brokers.registry import registry


def test_registry_exposes_supported_broker_names():
    assert {"dhan", "groww", "angelone"}.issubset(set(registry.names()))


def test_placeholder_brokers_are_registered_but_have_no_live_capability():
    assert registry.get("groww") is GrowwAdapter
    assert registry.get("angel one") is AngelOneAdapter
    assert GrowwAdapter().capabilities == frozenset()
    assert AngelOneAdapter().capabilities == frozenset()


def test_unsupported_adapter_fails_closed():
    with pytest.raises(NotImplementedError):
        UnsupportedBrokerAdapter(broker_name="groww").get_orders()


def test_capabilities_never_imply_live_execution():
    result = capabilities_for(frozenset({"orders", "historical_data"}))
    assert result.orders is True
    assert result.historical_data is True
    assert result.paper_execution is True
    assert result.live_execution is False


def test_broker_errors_are_normalized_without_provider_details():
    result = normalize_broker_error(Exception("401 invalid access token secret=abc123"))
    assert result.code is BrokerErrorCode.AUTHENTICATION
    assert result.retryable is False
    assert "abc123" not in result.message


def test_rate_limit_and_timeout_are_retryable():
    assert normalize_broker_error(Exception("429 too many requests")).retryable is True
    assert normalize_broker_error(Exception("request timed out")).retryable is True
