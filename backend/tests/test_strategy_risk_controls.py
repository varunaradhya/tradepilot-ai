from app.services.algo_strategy import StrategyConfig, generate_regime_momentum_signal


def _bars(count=80, atr_size=1.0):
    closes = [100 + i * 0.5 for i in range(count)]
    highs = [value + atr_size for value in closes]
    lows = [value - atr_size for value in closes]
    volumes = [2000.0 for _ in closes]
    volumes[-1] = 5000.0
    return closes, highs, lows, volumes


def test_signal_rejects_low_risk_reward():
    closes, highs, lows, volumes = _bars()
    config = StrategyConfig(stop_atr=2.0, target_atr=2.5, min_risk_reward=1.8, volume_multiplier=0.0)
    signal = generate_regime_momentum_signal(closes, highs, lows, volumes, config)
    assert signal.action == "NEUTRAL"
    assert "RISK_REWARD_TOO_LOW" in signal.reason


def test_signal_rejects_extreme_volatility():
    closes, highs, lows, volumes = _bars(80, atr_size=20.0)
    config = StrategyConfig(max_atr_percent=0.08, volume_multiplier=0.0)
    signal = generate_regime_momentum_signal(closes, highs, lows, volumes, config)
    assert signal.action == "NEUTRAL"
    assert "VOLATILITY_FILTER_FAILED" in signal.reason
