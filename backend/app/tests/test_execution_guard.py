from app.services.broker_adapters import CanonicalOrder
from app.services.execution_guard import ExecutionContext, authorize_order


def _order(side="BUY", quantity=1, price=None):
    return CanonicalOrder(symbol="RELIANCE", side=side, quantity=quantity, price=price)


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


def test_quantity_limit_blocks_oversized_paper_order():
    result = authorize_order(
        ExecutionContext("Dhan", strategy_ready=True, risk_approved=True, max_quantity=10),
        _order(quantity=11),
    )
    assert result.allowed is False
    assert result.reason == "QUANTITY_LIMIT_EXCEEDED"


def test_quantity_limit_allows_order_at_boundary():
    result = authorize_order(
        ExecutionContext("Dhan", strategy_ready=True, risk_approved=True, max_quantity=10),
        _order(quantity=10),
    )
    assert result.allowed is True


def test_order_value_limit_blocks_oversized_limit_order():
    result = authorize_order(
        ExecutionContext("Dhan", strategy_ready=True, risk_approved=True, max_order_value=10000),
        _order(quantity=101, price=100.0),
    )
    assert result.allowed is False
    assert result.reason == "ORDER_VALUE_LIMIT_EXCEEDED"


def test_order_value_limit_allows_order_at_boundary():
    result = authorize_order(
        ExecutionContext("Dhan", strategy_ready=True, risk_approved=True, max_order_value=10000),
        _order(quantity=100, price=100.0),
    )
    assert result.allowed is True


def test_order_value_limit_requires_verifiable_price():
    result = authorize_order(
        ExecutionContext("Dhan", strategy_ready=True, risk_approved=True, max_order_value=10000),
        _order(quantity=10),
    )
    assert result.allowed is False
    assert result.reason == "ORDER_VALUE_UNVERIFIABLE"
