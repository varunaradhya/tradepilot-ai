from datetime import datetime, timedelta, timezone

from app.brokers.registry import registry
from app.services.broker_sandbox import certify_broker_adapter
from app.services.market_data_health import evaluate_market_data_freshness


def test_market_data_watchdog_fails_closed_when_missing():
    health = evaluate_market_data_freshness(None)
    assert health.fresh is False
    assert health.reason == "NO_MARKET_DATA"


def test_market_data_watchdog_rejects_naive_timestamp():
    health = evaluate_market_data_freshness(datetime.now())
    assert health.fresh is False
    assert health.reason == "NAIVE_TIMESTAMP_REJECTED"


def test_market_data_watchdog_rejects_future_data():
    now = datetime.now(timezone.utc)
    health = evaluate_market_data_freshness(now + timedelta(seconds=1), now=now)
    assert health.fresh is False
    assert health.reason == "FUTURE_TIMESTAMP_REJECTED"


def test_market_data_watchdog_rejects_stale_data():
    now = datetime.now(timezone.utc)
    health = evaluate_market_data_freshness(now - timedelta(seconds=121), now=now)
    assert health.fresh is False
    assert health.reason == "STALE_MARKET_DATA"


def test_market_data_watchdog_accepts_fresh_data():
    now = datetime.now(timezone.utc)
    health = evaluate_market_data_freshness(now - timedelta(seconds=30), now=now)
    assert health.fresh is True
    assert health.reason == "FRESH"


def test_dhan_sandbox_contract_is_read_only():
    result = certify_broker_adapter("dhan")
    assert result["certified"] is True
    assert result["mode"] == "SANDBOX_READ_ONLY"
    assert result["live_execution_allowed"] is False
    assert result["forbidden_live_capabilities"] == []


def test_unsupported_broker_is_not_certified():
    result = certify_broker_adapter("unknown")
    assert result["certified"] is False
    assert result["live_execution_allowed"] is False


def test_all_registered_adapters_cannot_gain_live_capability():
    for broker in registry.names():
        result = certify_broker_adapter(broker)
        assert result["live_execution_allowed"] is False
