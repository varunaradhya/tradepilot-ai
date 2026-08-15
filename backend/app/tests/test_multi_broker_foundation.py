from datetime import datetime, timezone, timedelta

import pytest

from app.services.broker_adapters import CanonicalOrder, get_broker_adapter
from app.services.broker_capabilities import get_broker_capabilities, normalize_broker_name, live_execution_enabled
from app.services.broker_error import normalize_broker_error
from app.services.market_data_quality import validate_intraday_candles, is_indian_cash_market_time


def test_broker_aliases_and_capabilities_are_normalized():
    assert normalize_broker_name("Angel One SmartAPI") == "ANGELONE"
    assert get_broker_capabilities("Dhan").historical_data is True
    assert get_broker_capabilities("Groww").portfolio is True


def test_all_supported_adapters_block_live_orders():
    order = CanonicalOrder("TCS", "BUY", 1)
    for broker in ("Dhan", "Groww", "Angel One"):
        adapter = get_broker_adapter(broker)
        assert adapter.capabilities().paper_orders is True
        assert live_execution_enabled(broker) is False
        with pytest.raises(RuntimeError, match="LIVE_ORDER_EXECUTION_DISABLED"):
            adapter.place_order(order)


def test_broker_errors_are_normalized_without_exposing_details():
    result = normalize_broker_error("Dhan", RuntimeError("401 token=secret-value"))
    assert result.code == "AUTHENTICATION"
    assert str(result) == "Broker request failed safely"
    assert "secret-value" not in str(result)


def test_market_data_quality_detects_duplicates_and_missing_intervals():
    base = datetime(2026, 8, 14, 9, 15, tzinfo=timezone.utc)
    duplicate = [{"timestamp": base}, {"timestamp": base}]
    assert validate_intraday_candles(duplicate).duplicate is True

    rows = [{"timestamp": base}, {"timestamp": base + timedelta(minutes=15)}]
    result = validate_intraday_candles(rows, expected_minutes=5)
    assert result.missing_intervals == 2
    assert result.reason == "MISSING_INTERVALS"


def test_market_session_boundaries_are_explicit():
    assert is_indian_cash_market_time(__import__("datetime").time(9, 15))
    assert is_indian_cash_market_time(__import__("datetime").time(15, 30))
    assert not is_indian_cash_market_time(__import__("datetime").time(9, 14))
    assert not is_indian_cash_market_time(__import__("datetime").time(15, 31))
