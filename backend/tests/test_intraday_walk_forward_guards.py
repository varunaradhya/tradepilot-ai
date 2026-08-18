import pytest

from app.services.intraday_backtest import IntradayBacktestConfig
from app.services.intraday_walk_forward import run_fixed_parameter_walk_forward


def test_walk_forward_rejects_overlapping_validation_windows():
    rows = [{"timestamp": index, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1000} for index in range(100)]
    with pytest.raises(ValueError, match="overlapping validation windows"):
        run_fixed_parameter_walk_forward(rows, train_size=20, validation_size=10, step=5, config=IntradayBacktestConfig())
