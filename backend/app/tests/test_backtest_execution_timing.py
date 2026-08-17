from app.services import backtest_service
from app.services.algo_strategy import Signal, StrategyConfig
from app.services.backtest_service import BacktestConfig, run_daily_backtest


def _rows(count: int = 63):
    return [
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1000}
        for _ in range(count)
    ]


def test_daily_signal_cannot_fill_on_signal_bar(monkeypatch):
    def fake_signal(closes, highs, lows, volumes, config=StrategyConfig()):
        return Signal("BUY", 100.0, 100.0, 90.0, 120.0, ("TEST",))

    monkeypatch.setattr(backtest_service, "generate_regime_momentum_signal", fake_signal)
    rows = _rows()
    rows[61]["open"] = 110.0
    rows[61]["close"] = 110.0

    result = run_daily_backtest(rows, BacktestConfig(initial_capital=100000.0, slippage_rate=0.0, brokerage_rate=0.0))

    assert result["trades"] == 1
    assert result["trades_detail"][0]["entry"] == 110.0


def test_last_bar_signal_is_not_executed(monkeypatch):
    def fake_signal(closes, highs, lows, volumes, config=StrategyConfig()):
        return Signal("BUY", 100.0, 100.0, 90.0, 120.0, ("TEST",))

    monkeypatch.setattr(backtest_service, "generate_regime_momentum_signal", fake_signal)
    result = run_daily_backtest(
        _rows(61),
        BacktestConfig(initial_capital=100000.0, slippage_rate=0.0, brokerage_rate=0.0),
    )

    assert result["trades"] == 0


def test_gap_below_stop_does_not_fill_at_unreachable_stop(monkeypatch):
    def fake_signal(closes, highs, lows, volumes, config=StrategyConfig()):
        return Signal("BUY", 100.0, 100.0, 85.0, 120.0, ("TEST",))

    monkeypatch.setattr(backtest_service, "generate_regime_momentum_signal", fake_signal)
    rows = _rows()
    rows[61]["open"] = 80.0
    rows[61]["close"] = 80.0

    result = run_daily_backtest(rows, BacktestConfig(initial_capital=100000.0, slippage_rate=0.0, brokerage_rate=0.0))

    assert result["trades"] == 1
    trade = result["trades_detail"][0]
    assert trade["entry"] == 80.0
    assert trade["exit"] == 80.0
    assert trade["reason"] == "STOP_GAP"
