from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest


def test_backtest_accepts_v2a():
    result = run_intraday_backtest(
        [],
        IntradayBacktestConfig(strategy_version="V2A"),
    )
    assert result["strategy_version"] == "V2A"
    assert result["trades"] == 0
