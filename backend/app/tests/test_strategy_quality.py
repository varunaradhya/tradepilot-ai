from app.services.strategy_quality import score_long_setup
from app.services.intraday_strategy import IntradayConfig, generate_intraday_signal


def _series(n=60):
    closes = [100 + i * 0.35 for i in range(n)]
    highs = [p + 0.3 for p in closes]
    lows = [p - 0.25 for p in closes]
    return closes, highs, lows


def test_quality_score_is_deterministic_and_explainable():
    closes, _, _ = _series()
    result = score_long_setup(closes, 118.0, 116.0, 2.0, 0.8)
    assert 0 <= result.score <= 100
    assert result.regime == "TRENDING_UP"
    assert result.trend_score > 0
    assert result.volume_score > 0


def test_quality_score_identifies_sideways_regime():
    closes = [100.0] * 60
    result = score_long_setup(closes, 100.0, 100.0, 2.0, 0.8)
    assert result.regime == "SIDEWAYS"


def test_quality_score_identifies_down_regime():
    closes = [120 - i * 0.35 for i in range(60)]
    result = score_long_setup(closes, 100.0, 102.0, 2.0, 0.8)
    assert result.regime == "TRENDING_DOWN"


def test_intraday_config_rejects_invalid_quality_threshold():
    try:
        generate_intraday_signal([], [], [], [], [], config=IntradayConfig(min_quality_score=101))
    except ValueError as exc:
        assert "min_quality_score" in str(exc)
    else:
        raise AssertionError("invalid quality threshold should fail")


def test_intraday_signal_exposes_quality_metadata_on_buy():
    closes, highs, lows = _series()
    opens = [p - 0.05 for p in closes]
    volumes = [1000.0] * 59 + [2200.0]
    highs[-1] = max(highs[-1], 130.0)
    closes[-1] = 130.0
    result = generate_intraday_signal(opens, highs, lows, closes, volumes, opening_high=120.0)
    assert result["action"] == "BUY"
    assert result["regime"] == "TRENDING_UP"
    assert "quality_score" in result
    assert set(result["quality_components"]) == {"trend", "momentum", "volume", "volatility"}


def test_intraday_signal_can_disable_regime_gate_for_research_comparison():
    closes, highs, lows = _series()
    opens = [p - 0.05 for p in closes]
    volumes = [1000.0] * 59 + [2200.0]
    result = generate_intraday_signal(
        opens, highs, lows, closes, volumes, opening_high=120.0,
        config=IntradayConfig(require_trending_regime=False, min_quality_score=0),
    )
    assert result["action"] == "BUY"
