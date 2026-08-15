from app.services.position_risk import PositionRiskConfig, calculate_long_position


def test_position_size_uses_stop_distance_and_risk_budget():
    result = calculate_long_position(entry=100, stop=95, target=110, equity=100000)
    assert result.approved is True
    assert result.quantity == 100
    assert result.max_loss == 500
    assert result.risk_reward == 2.0


def test_position_size_respects_capital_limit():
    result = calculate_long_position(
        entry=1000, stop=990, target=1020, equity=100000,
        config=PositionRiskConfig(max_capital_pct=10, max_order_value=1_000_000),
    )
    assert result.quantity == 10
    assert result.capital_required == 10000


def test_daily_risk_remaining_limits_position_size():
    result = calculate_long_position(
        entry=100, stop=90, target=120, equity=100000, daily_risk_used=1500,
        config=PositionRiskConfig(daily_risk_budget=2000),
    )
    assert result.quantity == 50
    assert result.max_loss == 500


def test_daily_risk_limit_blocks_when_exhausted():
    result = calculate_long_position(
        entry=100, stop=95, target=110, equity=100000, daily_risk_used=2000,
    )
    assert result.approved is False
    assert result.reason == "DAILY_RISK_LIMIT"


def test_low_risk_reward_is_blocked():
    result = calculate_long_position(entry=100, stop=95, target=106, equity=100000)
    assert result.reason == "RISK_REWARD_TOO_LOW"


def test_invalid_long_stop_is_blocked():
    result = calculate_long_position(entry=100, stop=101, target=110, equity=100000)
    assert result.reason == "INVALID_LONG_STOP"


def test_invalid_target_is_blocked():
    result = calculate_long_position(entry=100, stop=95, target=99, equity=100000)
    assert result.reason == "INVALID_LONG_TARGET"


def test_order_value_cap_is_respected():
    result = calculate_long_position(
        entry=250, stop=240, target=270, equity=1_000_000,
        config=PositionRiskConfig(max_order_value=5000),
    )
    assert result.quantity == 20
    assert result.capital_required == 5000


def test_max_quantity_is_respected():
    result = calculate_long_position(
        entry=10, stop=9, target=12, equity=1_000_000,
        config=PositionRiskConfig(max_quantity=25, max_order_value=1_000_000),
    )
    assert result.quantity == 25


def test_tiny_risk_budget_blocks_trade():
    result = calculate_long_position(
        entry=1000, stop=900, target=1200, equity=1000,
    )
    assert result.reason == "RISK_BUDGET_TOO_SMALL"
