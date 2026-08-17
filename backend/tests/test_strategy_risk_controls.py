from app.services.algo_strategy import StrategyConfig, Signal, generate_regime_momentum_signal, position_size


def _bars(n=80, base=100.0, step=0.2, atr_size=2.0):
    closes = [base + i * step for i in range(n)]
    highs = [x + atr_size for x in closes]
    lows = [x - atr_size for x in closes]
    volumes = [1000.0] * n
    return closes, highs, lows, volumes


def test_position_size_never_exceeds_risk_or_allocation():
    config = StrategyConfig(risk_per_trade=0.005, max_position_fraction=0.20)
    qty = position_size(100000, 100, 95, config)
    assert qty * 5 <= 500
    assert qty * 100 <= 20000


def test_signal_rejects_low_risk_reward():
    closes, highs, lows, volumes = _bars()
    config = StrategyConfig(stop_atr=2.0, target_atr=2.5, min_risk_reward=1.8)
    signal = generate_regime_momentum_signal(closes, highs, lows, volumes, config)
    assert signal.action == "NEUTRAL"
    assert "RISK_REWARD_TOO_LOW" in signal.reason


def test_signal_rejects_extreme_volatility():
    closes, highs, lows, volumes = _bars(80, atr_size=20.0)
    config = StrategyConfig(max_atr_percent=0.08)
    signal = generate_regime_momentum_signal(closes, highs, lows, volumes, config)
    assert signal.action == "NEUTRAL"
    assert "VOLATILITY_FILTER_FAILED" in signal.reason


def test_signal_buy_contains_explicit_rr_reason_when_valid():
    closes, highs, lows, volumes = _bars(80, atr_size=1.0)
    config = StrategyConfig(min_atr_percent=0.001, max_atr_percent=0.08, min_risk_reward=1.5)
    # Force a breakout on the final bar while retaining a valid volume baseline.
    closes[-1] = max(highs[-21:-1]) + 1.0
    highs[-1] = closes[-1] + 1.0
    lows[-1] = closes[-1] - 1.0
    volumes[-1] = 1500.0
    signal = generate_regime_momentum_signal(closes, highs, lows, volumes, config)
    assert signal.action == "BUY"
    assert any(reason.startswith("RR_") for reason in signal.reason)
