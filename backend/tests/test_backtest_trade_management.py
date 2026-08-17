from app.services import backtest_service
from app.services.algo_strategy import Signal, StrategyConfig
from app.services.backtest_service import BacktestConfig, run_daily_backtest


def _rows(count=70):
    return [
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1000}
        for _ in range(count)
    ]


def test_max_holding_period_forces_exit(monkeypatch):
    def fake_signal(closes, highs, lows, volumes, config=StrategyConfig()):
        return Signal("BUY", 100.0, 100.0, 90.0, 130.0, ("TEST",))

    monkeypatch.setattr(backtest_service, "generate_regime_momentum_signal", fake_signal)
    strategy = StrategyConfig(max_holding_bars=2)
    result = run_daily_backtest(
        _rows(),
        BacktestConfig(initial_capital=100000, brokerage_rate=0, slippage_rate=0, strategy=strategy),
    )

    assert result["trades"] >= 1
    assert any(trade["reason"] == "MAX_HOLD" for trade in result["trades_detail"])
    assert any(trade["holding_bars"] == 2 for trade in result["trades_detail"] if trade["reason"] == "MAX_HOLD")
