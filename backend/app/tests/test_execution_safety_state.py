from app.services.broker_adapters import CanonicalOrder
from app.services.execution_guard import ExecutionContext, ExecutionSafetyState, authorize_order


def _order():
    return CanonicalOrder(symbol="RELIANCE", side="BUY", quantity=1)


def _ready_context(key: str):
    return ExecutionContext(
        "Dhan",
        strategy_ready=True,
        risk_approved=True,
        idempotency_key=key,
    )


def test_duplicate_order_intent_is_blocked():
    state = ExecutionSafetyState()
    context = _ready_context("signal-123")
    first = authorize_order(context, _order(), state)
    second = authorize_order(context, _order(), state)

    assert first.allowed is True
    assert second.allowed is False
    assert second.reason == "DUPLICATE_ORDER_INTENT"


def test_kill_switch_blocks_new_orders():
    state = ExecutionSafetyState()
    state.activate_kill_switch()
    result = authorize_order(_ready_context("signal-456"), _order(), state)

    assert result.allowed is False
    assert result.reason == "KILL_SWITCH_ACTIVE"


def test_kill_switch_can_be_cleared_for_paper_execution():
    state = ExecutionSafetyState()
    state.activate_kill_switch()
    state.deactivate_kill_switch()
    result = authorize_order(_ready_context("signal-789"), _order(), state)

    assert result.allowed is True
    assert result.reason == "PAPER_ORDER_AUTHORIZED"
