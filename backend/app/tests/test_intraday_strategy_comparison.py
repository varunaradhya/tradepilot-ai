from app.services.intraday_backtest import IntradayBacktestConfig
from app.services.intraday_strategy_comparison import compare_intraday_strategies


def _rows(n=30):
    rows = []
    for i in range(n):
        close = 100 + i * 0.4
        rows.append({"session": "D1", "open": close - .1, "high": close + 1, "low": close - 1, "close": close, "volume": 1000 + i * 20, "market_close": close * 0.999, "sector_close": close * 1.001})
    return rows


def test_v1_v2_comparison_uses_identical_execution_assumptions():
    result = compare_intraday_strategies(_rows(), IntradayBacktestConfig(slippage_rate=0.001))
    assert result["assumptions"]["slippage_rate"] == 0.001
    assert result["assumptions"]["parameter_selection"] is False
    assert result["v1"]["strategy_version"] == "V1"
    assert result["v2"]["strategy_version"] == "V2"
    assert "return_percent" in result["delta"]
