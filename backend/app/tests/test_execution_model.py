import pytest

from app.services.execution_model import ExecutionModelConfig


def test_buy_fill_includes_spread_slippage_and_impact():
    model = ExecutionModelConfig(slippage_rate=0.001, spread_bps=20, market_impact_bps=10)
    assert model.fill_price(100.0, "BUY", 100000) > 100.0


def test_sell_fill_is_below_reference():
    model = ExecutionModelConfig(slippage_rate=0.001, spread_bps=20)
    assert model.fill_price(100.0, "SELL", 100000) < 100.0


def test_participation_limits_fill_quantity():
    model = ExecutionModelConfig(max_volume_participation=0.1)
    assert model.max_fill_quantity(500, 1000) == 100


def test_zero_volume_can_block_fill_when_participation_is_enabled():
    model = ExecutionModelConfig(max_volume_participation=0.1)
    assert model.max_fill_quantity(500, 0) == 0


def test_invalid_execution_parameters_are_rejected():
    with pytest.raises(ValueError):
        ExecutionModelConfig(spread_bps=-1)
    with pytest.raises(ValueError):
        ExecutionModelConfig(max_volume_participation=1.1)
