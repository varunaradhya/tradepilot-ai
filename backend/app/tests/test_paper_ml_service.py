import json
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.models.paper_trade_learning import PaperTradeLearningEvent
from app.services.paper_ml_service import learning_features, set_deployment


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


def test_ml_deployment_rejects_live_mode():
    try:
        set_deployment(None, 1, "V1", "LIVE")
    except ValueError as exc:
        assert "live mode is disabled" in str(exc)
    else:
        raise AssertionError("LIVE ML deployment must remain disabled")


def test_learning_event_has_json_features():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[PaperTradeLearningEvent.__table__])
    with Session(engine) as db:
        event = PaperTradeLearningEvent(
            user_id=1, symbol="RELIANCE", session="2026-09-28",
            strategy_version="V1", model_version="RULES_V1",
            fingerprint="a" * 64, features_json=json.dumps({"volume_ratio": 1.5}),
            label=1, pnl=100.0, r_multiple=1.0, exit_reason="TARGET",
        )
        db.add(event)
        db.commit()
        assert json.loads(event.features_json)["volume_ratio"] == 1.5


def test_learning_event_requires_feature_event_time():
    from app.services.paper_ml_service import record_trade_outcome

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[PaperTradeLearningEvent.__table__])
    with Session(engine) as db:
        trade = {
            "symbol": "TCS",
            "entry": 100.0,
            "stop": 98.0,
            "quantity": 10,
            "pnl": 50.0,
            "learning_features": {"volume_ratio": 1.5},
        }
        try:
            record_trade_outcome(db, 1, "2026-09-29", trade, commit=False)
        except ValueError as exc:
            assert "event timestamp" in str(exc)
        else:
            raise AssertionError("Learning event without feature-time must be rejected")


def test_learning_event_persists_market_feature_time():
    from app.services.paper_ml_service import record_trade_outcome

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[PaperTradeLearningEvent.__table__])
    with Session(engine) as db:
        trade = {
            "symbol": "TCS",
            "entry": 100.0,
            "stop": 98.0,
            "quantity": 10,
            "pnl": 50.0,
            "entry_time": "2026-09-29T09:25:00+05:30",
            "learning_features": {"volume_ratio": 1.5},
        }
        event = record_trade_outcome(db, 1, "2026-09-29", trade, commit=False)
        assert event.event_at == datetime.fromisoformat("2026-09-29T09:25:00+05:30")


def test_learning_events_are_ordered_by_feature_time_not_insert_id():
    from app.services.paper_ml_service import _events

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[PaperTradeLearningEvent.__table__])
    with Session(engine) as db:
        later = PaperTradeLearningEvent(
            user_id=1, symbol="TCS", session="2026-09-29",
            strategy_version="V1", model_version="RULES_V1", fingerprint="a" * 64,
            features_json="{}", label=1, pnl=10.0, r_multiple=1.0,
            exit_reason="TARGET", event_at=datetime(2026, 9, 29, 10, tzinfo=timezone.utc),
        )
        earlier = PaperTradeLearningEvent(
            user_id=1, symbol="TCS", session="2026-09-29",
            strategy_version="V1", model_version="RULES_V1", fingerprint="b" * 64,
            features_json="{}", label=0, pnl=-10.0, r_multiple=-1.0,
            exit_reason="STOP", event_at=datetime(2026, 9, 29, 9, tzinfo=timezone.utc),
        )
        db.add_all([later, earlier])
        db.commit()
        ordered = _events(db, 1, "V1")
        assert ordered[0].event_at.hour == 9
        assert ordered[1].event_at.hour == 10


def test_ml_qualification_gate_uses_validation_metrics():
    from app.services.paper_ml_service import _qualification_gate

    assert _qualification_gate({
        "accuracy": 0.60,
        "brier": 0.20,
        "roc_auc": 0.55,
    }) is True
    assert _qualification_gate({
        "accuracy": 0.49,
        "brier": 0.10,
        "roc_auc": 0.90,
    }) is False
