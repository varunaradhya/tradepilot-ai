from app.services.broker_adapters import CanonicalOrder
from app.services.execution_guard import ExecutionContext, authorize_order


def order(side="BUY"):
    return CanonicalOrder(symbol="TCS", side=side, quantity=1)


def ready(**kwargs):
    base = dict(
        broker="DHAN",
        mode="PAPER",
        market_data_healthy=True,
        strategy_ready=True,
        risk_approved=True,
        long_only=True,
    )
    base.update(kwargs)
    return ExecutionContext(**base)


def test_ready_paper_buy_is_authorized():
    result = authorize_order(ready(), order())
    assert result.allowed is True
    assert result.reason == "PAPER_ORDER_AUTHORIZED"


def test_strategy_not_ready_blocks_paper_order():
    result = authorize_order(ready(strategy_ready=False), order())
    assert result.reason == "STRATEGY_NOT_READY"


def test_risk_not_approved_blocks_paper_order():
    result = authorize_order(ready(risk_approved=False), order())
    assert result.reason == "RISK_NOT_APPROVED"


def test_unhealthy_market_data_blocks_paper_order():
    result = authorize_order(ready(market_data_healthy=False), order())
    assert result.reason == "MARKET_DATA_UNSAFE"


def test_long_only_policy_blocks_sell():
    result = authorize_order(ready(), order("SELL"))
    assert result.reason == "LONG_ONLY_POLICY"


def test_live_mode_is_always_locked():
    result = authorize_order(ready(mode="LIVE"), order())
    assert result.allowed is False
    assert result.reason == "LIVE_ORDER_EXECUTION_DISABLED"


def test_unknown_mode_is_rejected():
    result = authorize_order(ready(mode="UNKNOWN"), order())
    assert result.reason == "UNSUPPORTED_EXECUTION_MODE"


def test_invalid_symbol_is_rejected_before_strategy_gate():
    bad = CanonicalOrder(symbol="", side="BUY", quantity=1)
    result = authorize_order(ready(strategy_ready=False), bad)
    assert result.reason == "INVALID_SYMBOL"


def test_zero_quantity_is_rejected():
    bad = CanonicalOrder(symbol="TCS", side="BUY", quantity=0)
    result = authorize_order(ready(), bad)
    assert result.reason == "INVALID_QUANTITY"


def test_invalid_limit_price_is_rejected():
    bad = CanonicalOrder(symbol="TCS", side="BUY", quantity=1, order_type="LIMIT")
    result = authorize_order(ready(), bad)
    assert result.reason == "INVALID_LIMIT_PRICE"


def test_angelone_alias_uses_same_safety_policy():
    result = authorize_order(ready(broker="Angel One SmartAPI"), order())
    assert result.allowed is True
    assert result.normalized_broker == "ANGELONE"


def test_groww_uses_same_paper_safety_policy():
    result = authorize_order(ready(broker="Groww"), order())
    assert result.allowed is True
    assert result.normalized_broker == "GROWW"
