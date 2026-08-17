from app.services import backtest_service
from app.services.algo_strategy import Signal, StrategyConfig
from app.services.backtest_service import BacktestConfig, run_daily_backtest


def _rows(count: int = 63, open_price: float = 100.0, close_price: float = 100.0):
    return [
        {
            "open": open_price,
            "high": max(open_price, close_price) + 1.0,
            "low": min(open_price, close_price) - 1.0,
            "close": close_price,
            "volume": 1000,
        }
        for _ in range(count)
    ]


def test_signal_is_executed_on_following_bar_open(monkeypatch):
    calls = []

    def fake_signal(closes, highs, lows, volumes, config=StrategyConfig()):
        calls.append(len(closes))
        return Signal("BUY", 100.0, 100.0, 90.0, 120.0, ("TEST",))

    monkeypatch.setattr(backtest_service, "generate_regime_momentum_signal", fake_signal)
    rows = _rows()
    rows[60]["close"] = 100.0
    rows[61]["open"] = 110.0
    rows[61]["close"] = 110.0

    result = run_daily_backtest(rows, BacktestConfig(initial_capital=100000.0, slippage_rate=0.0, brokerage_rate=0.0))

    assert result["trades"] == 1
    # The signal is generated after bar 60 and must fill at bar 61's open.
    assert result["trades_detail"][0]["entry"] == 110.0
    assert 60 in calls
    assert 61 in calls


def test_final_bar_signal_is_not_executed_without_a_following_bar(monkeypatch):
    def fake_signal(closes, highs, lows, volumes, config=StrategyConfig()):
        return Signal("BUY", 100.0, 100.0, 90.0, 120.0, ("TEST",))

    monkeypatch.setattr(backtest_service, "generate_regime_momentum_signal", fake_signal)
    result = run_daily_backtest(
        _rows(61),
        BacktestConfig(initial_capital=100000.0, slippage_rate=0.0, brokerage_rate=0.0),
    )

    assert result["trades"] == 0


def test_gap_through_stop_is_filled_at_open(monkeypatch):
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
