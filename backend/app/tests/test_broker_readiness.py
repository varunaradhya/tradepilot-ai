import pytest

from app.services.broker_adapters import CanonicalOrder, get_broker_adapter
from app.services.broker_capabilities import broker_integration_status, live_execution_enabled


def test_broker_status_does_not_claim_unimplemented_adapters_are_ready():
    assert broker_integration_status("Dhan") == "FOUNDATION"
    assert broker_integration_status("Groww") == "FOUNDATION_ONLY"
    assert broker_integration_status("Angel One") == "FOUNDATION_ONLY"


def test_live_execution_is_disabled_for_every_supported_broker():
    for broker in ("Dhan", "Groww", "Angel One"):
        assert live_execution_enabled(broker) is False


@pytest.mark.parametrize(
    "order, reason",
    [
        (CanonicalOrder("", "BUY", 1), "INVALID_SYMBOL"),
        (CanonicalOrder("TCS", "HOLD", 1), "INVALID_SIDE"),
        (CanonicalOrder("TCS", "BUY", 0), "INVALID_QUANTITY"),
        (CanonicalOrder("TCS", "BUY", 1, order_type="STOP"), "INVALID_ORDER_TYPE"),
        (CanonicalOrder("TCS", "BUY", 1, order_type="LIMIT"), "INVALID_LIMIT_PRICE"),
    ],
)
def test_canonical_orders_fail_closed_before_execution(order, reason):
    adapter = get_broker_adapter("Dhan")
    with pytest.raises(ValueError, match=reason):
        adapter.place_order(order)


def test_valid_canonical_order_still_cannot_execute_live():
    adapter = get_broker_adapter("Dhan")
    order = CanonicalOrder("TCS", "BUY", 1)
    with pytest.raises(RuntimeError, match="LIVE_ORDER_EXECUTION_DISABLED"):
        adapter.place_order(order)
