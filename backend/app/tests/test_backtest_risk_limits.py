from app.services import backtest_service
from app.services.algo_strategy import Signal, StrategyConfig
from app.services.backtest_service import BacktestConfig, run_daily_backtest


def _intraday_rows(count: int = 66):
    rows = []
    for i in range(count):
        minute = 9 * 60 + 15 + i
        hour, minute_value = divmod(minute, 60)
        rows.append({
            "timestamp": f"2026-08-17T{hour:02d}:{minute_value:02d}:00",
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1000,
        })
    return rows


def test_intraday_timestamps_share_one_daily_risk_session(monkeypatch):
    def fake_signal(closes, highs, lows, volumes, config=StrategyConfig()):
        return Signal("BUY", 100.0, 100.0, 99.0, 101.0, ("TEST",))

    monkeypatch.setattr(backtest_service, "generate_regime_momentum_signal", fake_signal)
    result = run_daily_backtest(
        _intraday_rows(),
        BacktestConfig(
            initial_capital=100000.0,
            brokerage_rate=0.0,
            slippage_rate=0.0,
            max_trades_per_day=1,
        ),
    )

    assert result["trades"] == 1
