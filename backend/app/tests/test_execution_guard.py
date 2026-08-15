from app.services.broker_adapters import CanonicalOrder
from app.services.execution_guard import ExecutionContext, authorize_order


def _order(side="BUY"):
    return CanonicalOrder(symbol="RELIANCE", side=side, quantity=1)


def test_paper_order_requires_strategy_readiness():
    result = authorize_order(
        ExecutionContext("Dhan", strategy_ready=False, risk_approved=True), _order()
    )
    assert result.allowed is False
    assert result.reason == "STRATEGY_NOT_READY"


def test_paper_order_requires_risk_approval():
    result = authorize_order(
        ExecutionContext("Dhan", strategy_ready=True, risk_approved=False), _order()
    )
    assert result.allowed is False
    assert result.reason == "RISK_NOT_APPROVED"


def test_unhealthy_market_data_blocks_paper_order():
    result = authorize_order(
        ExecutionContext("Dhan", market_data_healthy=False, strategy_ready=True, risk_approved=True),
        _order(),
    )
    assert result.allowed is False
    assert result.reason == "MARKET_DATA_UNSAFE"


def test_long_only_blocks_sell_first_execution():
    result = authorize_order(
        ExecutionContext("Dhan", strategy_ready=True, risk_approved=True), _order("SELL")
    )
    assert result.allowed is False
    assert result.reason == "LONG_ONLY_POLICY"


def test_live_mode_is_hard_locked_even_when_every_gate_passes():
    result = authorize_order(
        ExecutionContext("Dhan", mode="LIVE", strategy_ready=True, risk_approved=True), _order()
    )
    assert result.allowed is False
    assert result.reason == "LIVE_ORDER_EXECUTION_DISABLED"


def test_ready_paper_buy_is_authorized():
    result = authorize_order(
        ExecutionContext("Angel One SmartAPI", strategy_ready=True, risk_approved=True), _order()
    )
    assert result.allowed is True
    assert result.reason == "PAPER_ORDER_AUTHORIZED"
    assert result.normalized_broker == "ANGELONE"
