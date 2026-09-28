import json

from app.services.paper_ml_service import learning_features, set_deployment
from app.models.paper_trade_learning import PaperTradeLearningEvent


def test_learning_features_are_deterministic():
    signal = {
        "entry": 100.0, "stop": 98.0, "volume_ratio": 2.0, "atr": 1.5,
        "quality_score": 72, "risk_reward": 2.0, "gap_percent": 0.5,
        "ema_fast": 101.0, "ema_slow": 99.0, "regime": "TRENDING_UP",
        "opening_high": 100.0, "opening_low": 99.0,
    }
    features = learning_features(signal)
    assert features["volume_ratio"] == 2.0
    assert features["regime_trending_up"] == 1.0
    assert features["ema_spread_pct"] == 2.0
    assert features["stop_distance_pct"] == 2.0


def test_ml_deployment_rejects_live_mode(db_session):
    try:
        set_deployment(db_session, 1, "V1", "LIVE")
    except ValueError as exc:
        assert "live mode is disabled" in str(exc)
    else:
        raise AssertionError("LIVE ML deployment must remain disabled")


def test_learning_event_has_json_features(db_session):
    event = PaperTradeLearningEvent(
        user_id=1, symbol="RELIANCE", session="2026-09-28",
        strategy_version="V1", model_version="RULES_V1",
        fingerprint="a" * 64, features_json=json.dumps({"volume_ratio": 1.5}),
        label=1, pnl=100.0, r_multiple=1.0, exit_reason="TARGET",
    )
    db_session.add(event)
    db_session.commit()
    assert json.loads(event.features_json)["volume_ratio"] == 1.5
