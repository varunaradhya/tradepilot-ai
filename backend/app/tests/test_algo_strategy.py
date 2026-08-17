from app.services.algo_strategy import StrategyConfig, generate_regime_momentum_signal, position_size
from app.services.backtest_service import BacktestConfig, run_daily_backtest


def _trend_rows(n=100):
    rows = []
    price = 100.0
    for i in range(n):
        price += 0.8 if i % 3 else -0.8
        rows.append({"close": price, "high": price + 1.0, "low": price - 1.0, "volume": 2000.0})
    rows[-1]["close"] += 8
    rows[-1]["high"] += 8
    rows[-1]["volume"] = 5000.0
    return rows


def test_strategy_requires_all_filters():
    rows = _trend_rows()
    signal = generate_regime_momentum_signal(
        [r["close"] for r in rows], [r["high"] for r in rows], [r["low"] for r in rows], [r["volume"] for r in rows]
    )
    assert signal.action == "BUY"
    assert signal.stop < signal.entry < signal.target
    assert signal.score == 100


def test_strategy_is_neutral_with_insufficient_data():
    signal = generate_regime_momentum_signal([100, 101], [102, 103], [99, 100], [1000, 1000])
    assert signal.action == "NEUTRAL"
    assert signal.reason == ("INSUFFICIENT_DATA",)


def test_position_size_respects_risk_and_capital_limits():
    config = StrategyConfig(risk_per_trade=0.01, max_position_fraction=0.20)
    assert position_size(100000, 100, 95, config) == 200


def test_backtest_never_counts_same_candle_stop_and_target_as_target():
    rows = _trend_rows(100)
    result = run_daily_backtest(rows + [{"close": 150, "high": 160, "low": 80, "volume": 5000}], BacktestConfig(strategy=StrategyConfig(max_holding_bars=1000)))
    assert result["trades"] >= 1
    assert any(trade["reason"] == "STOP" for trade in result["trades_detail"])


def test_backtest_output_is_reproducible():
    rows = _trend_rows(120)
    config = BacktestConfig(initial_capital=100000)
    assert run_daily_backtest(rows, config) == run_daily_backtest(rows, config)
