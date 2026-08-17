from app.services import backtest_service
from app.services.algo_strategy import Signal, StrategyConfig
from app.services.backtest_service import BacktestConfig, run_daily_backtest


def test_entry_brokerage_is_not_charged_twice(monkeypatch):
    def fake_signal(closes, highs, lows, volumes, config=StrategyConfig()):
        return Signal("BUY", 100.0, 90.0, 90.0, 120.0, ("TEST",))

    monkeypatch.setattr(backtest_service, "generate_regime_momentum_signal", fake_signal)
    rows = []
    for _ in range(64):
        rows.append({"date": "2026-08-17", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 1000})
    rows[63]["close"] = 110.0

    result = run_daily_backtest(rows, BacktestConfig(initial_capital=100000.0, brokerage_rate=0.001, slippage_rate=0.0, strategy=StrategyConfig(max_holding_bars=1)))
    trade = result["trades_detail"][0]
    expected = trade["quantity"] * trade["exit"] * 0.999 - trade["quantity"] * trade["entry"] * 1.001
    assert abs(trade["pnl"] - expected) < 1e-6
