import pytest

from app.services.intraday_signal_engine import generate_long_intraday_signal


def series(up=True):
    closes = [100 + i * (0.35 if up else -0.35) for i in range(30)]
    highs = [x + 0.5 for x in closes]
    lows = [x - 0.5 for x in closes]
    volumes = [1000.0] * 29 + [1500.0]
    return closes, highs, lows, volumes


def test_breakout_long_signal_contains_risk_levels():
    closes, highs, lows, volumes = series()
    result = generate_long_intraday_signal(closes, highs, lows, volumes, opening_high=108)
    assert result.action == "BUY"
    assert result.entry is not None
    assert result.stop is not None
    assert result.target is not None
    assert result.risk_reward == 2.0
    assert "TREND_UP" in result.reasons
    assert "OPENING_HIGH_BREAKOUT" in result.reasons


def test_downtrend_does_not_create_long_signal():
    closes, highs, lows, volumes = series(False)
    result = generate_long_intraday_signal(closes, highs, lows, volumes, opening_high=95)
    assert result.action == "NEUTRAL"


def test_weak_volume_can_keep_setup_neutral():
    closes, highs, lows, _ = series()
    volumes = [1000.0] * 30
    result = generate_long_intraday_signal(closes, highs, lows, volumes, opening_high=108)
    assert result.action == "BUY"  # trend + breakout remain sufficient
    assert "VOLUME_CONFIRMATION" not in result.reasons


def test_insufficient_data_is_rejected():
    with pytest.raises(ValueError, match="INSUFFICIENT_DATA"):
        generate_long_intraday_signal([100.0] * 10, [101.0] * 10, [99.0] * 10, [1000.0] * 10)


def test_series_mismatch_is_rejected():
    with pytest.raises(ValueError, match="SERIES_LENGTH_MISMATCH"):
        generate_long_intraday_signal([100.0] * 20, [101.0] * 19, [99.0] * 20, [1000.0] * 20)


def test_invalid_risk_parameters_are_rejected():
    closes, highs, lows, volumes = series()
    with pytest.raises(ValueError, match="INVALID_RISK_PARAMETERS"):
        generate_long_intraday_signal(closes, highs, lows, volumes, reward_multiple=0)


def test_confidence_threshold_can_suppress_signal():
    closes, highs, lows, volumes = series()
    result = generate_long_intraday_signal(closes, highs, lows, volumes, opening_high=108, min_confidence=95)
    assert result.action == "NEUTRAL"
