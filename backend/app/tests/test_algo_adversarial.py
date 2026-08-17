from app.services.algo_strategy import StrategyConfig, generate_regime_momentum_signal
from app.services.backtest_service import BacktestConfig, run_daily_backtest
from app.services.strategy_diagnostics import diagnose_regime_momentum


def _rows(closes, volume=2000.0):
    return [
        {"close": float(c), "high": float(c) + 1.0, "low": float(c) - 1.0, "volume": float(volume)}
        for c in closes
    ]


def _healthy_trend(n=100):
    price = 100.0
    rows = []
    for i in range(n):
        price += 0.8 if i % 3 else -0.8
        rows.append({"close": price, "high": price + 1.0, "low": price - 1.0, "volume": 2000.0})
    rows[-1]["close"] += 8
    rows[-1]["high"] += 8
    rows[-1]["volume"] = 5000.0
    return rows


def test_bear_market_does_not_generate_long_signal():
    rows = _rows([200 - i * 1.2 for i in range(100)])
    signal = generate_regime_momentum_signal(
        [r["close"] for r in rows], [r["high"] for r in rows], [r["low"] for r in rows], [r["volume"] for r in rows]
    )
    assert signal.action == "NEUTRAL"


def test_sideways_market_does_not_generate_long_signal():
    closes = [100 + (1 if i % 2 else -1) for i in range(100)]
    rows = _rows(closes)
    signal = generate_regime_momentum_signal(
        [r["close"] for r in rows], [r["high"] for r in rows], [r["low"] for r in rows], [r["volume"] for r in rows]
    )
    assert signal.action == "NEUTRAL"


def test_false_breakout_without_volume_is_rejected():
    rows = _healthy_trend()
    rows[-1]["volume"] = 2000.0
    signal = generate_regime_momentum_signal(
        [r["close"] for r in rows], [r["high"] for r in rows], [r["low"] for r in rows], [r["volume"] for r in rows]
    )
    assert signal.action == "NEUTRAL"
    assert "VOLUME_FILTER_FAILED" in signal.reason


def test_gap_reversal_does_not_change_conservative_stop_priority():
    rows = _healthy_trend()
    rows.append({"close": 80.0, "high": 160.0, "low": 70.0, "volume": 10000.0})
    result = run_daily_backtest(rows, BacktestConfig(strategy=StrategyConfig(max_holding_bars=1000)))
    if result["trades_detail"]:
        assert any(t["reason"] in {"STOP", "END_OF_TEST", "STOP_GAP"} for t in result["trades_detail"])


def test_diagnostics_identify_failed_filter_without_changing_strategy():
    rows = _healthy_trend()
    rows[-1]["volume"] = 2000.0
    diagnostics = diagnose_regime_momentum(
        [r["close"] for r in rows], [r["high"] for r in rows], [r["low"] for r in rows], [r["volume"] for r in rows]
    )
    assert diagnostics["status"] == "FILTERS_BLOCKED"
    assert "volume" in diagnostics["failed_filters"]


def test_strategy_config_remains_conservative_by_default():
    config = StrategyConfig()
    assert config.risk_per_trade <= 0.005
    assert config.max_position_fraction <= 0.20
