from app.brokers.registry import registry
from app.services.broker_capabilities import get_broker_capabilities, live_execution_enabled
from app.services.broker_sandbox import certify_broker_adapter


FORBIDDEN_LIVE_CAPABILITIES = {"place_order", "modify_order", "cancel_order", "live_order"}
SUPPORTED_BROKERS = ("dhan", "groww", "angelone")


def test_every_registered_broker_is_live_execution_disabled():
    for broker in registry.names():
        assert live_execution_enabled(broker) is False
        capabilities = get_broker_capabilities(broker)
        assert capabilities.live_orders is False


def test_broker_sandbox_certification_never_authorizes_live_execution():
    for broker in SUPPORTED_BROKERS:
        result = certify_broker_adapter(broker)
        assert result["live_execution_allowed"] is False
        assert not set(result["forbidden_live_capabilities"]) & FORBIDDEN_LIVE_CAPABILITIES


def test_unknown_broker_fails_closed():
    result = certify_broker_adapter("not-a-real-broker")
    assert result["certified"] is False
    assert result["live_execution_allowed"] is False


def test_capability_contract_has_no_live_order_provider_enabled():
    for broker in SUPPORTED_BROKERS:
        capabilities = get_broker_capabilities(broker)
        assert capabilities.live_orders is False
        assert live_execution_enabled(broker) is False
