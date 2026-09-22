from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.paper_signal_request import PaperSignalRequest
from app.models.paper_trade import PaperTrade
from app.services.paper_signal_request_service import claim_request, complete_request, replay_response, request_fingerprint, reconcile_pending_request


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def signal():
    return {
        "symbol": "NIFTY",
        "interval": "5",
        "strategy_version": "V1",
        "session": "2026-09-21",
        "action": "BUY",
        "entry": 120,
        "stop": 90,
        "target": 180,
        "lot_size": 75,
    }


def test_paper_signal_request_is_idempotent_and_replays_response():
    db = make_db()
    first, claimed = claim_request(db, 1, "fno-dummy-001", signal())
    assert claimed is True

    response = {"mode": "PAPER_ONLY", "accepted": True, "request_id": "fno-dummy-001"}
    complete_request(db, first, response)

    second, claimed_again = claim_request(db, 1, "fno-dummy-001", signal())
    assert claimed_again is False
    assert second.id == first.id
    assert replay_response(second) == response


def test_request_fingerprint_changes_when_execution_inputs_change():
    base = signal()
    changed = {**base, "entry": 121}
    assert request_fingerprint(base) != request_fingerprint(changed)


def test_request_id_cannot_be_reused_for_a_different_signal():
    db = make_db()
    claim_request(db, 1, "fno-dummy-002", signal())
    changed = {**signal(), "target": 181}
    import pytest
    with pytest.raises(ValueError, match="different signal"):
        claim_request(db, 1, "fno-dummy-002", changed)


def test_request_fingerprint_changes_when_option_contract_changes():
    base = {**signal(), "decision": "QUALIFIED", "contract": {"security_id": "123", "strike": 25000, "option_type": "CE"}}
    changed = {**base, "contract": {"security_id": "124", "strike": 25000, "option_type": "CE"}}
    assert request_fingerprint(base) != request_fingerprint(changed)


def test_request_fingerprint_changes_when_completed_candle_changes():
    base = {**signal(), "candle_timestamp": 1758440700}
    changed = {**base, "candle_timestamp": 1758441000}
    assert request_fingerprint(base) != request_fingerprint(changed)


def test_pending_request_stale_detection_handles_naive_utc():
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace
    from app.services.paper_signal_request_service import is_stale_pending_request

    created = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=10)
    record = SimpleNamespace(decision="PENDING", created_at=created)
    assert is_stale_pending_request(record, max_age_seconds=300)


def test_fresh_pending_request_is_not_reported_stale():
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace
    from app.services.paper_signal_request_service import is_stale_pending_request

    now = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)
    record = SimpleNamespace(decision="PENDING", created_at=now - timedelta(seconds=299))
    assert is_stale_pending_request(record, max_age_seconds=300, now=now) is False


def test_stale_pending_request_is_recovery_only_and_not_replayable():
    from datetime import datetime, timedelta, timezone
    from app.services.paper_signal_request_service import is_stale_pending_request, replay_response
    from types import SimpleNamespace

    now = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)
    record = SimpleNamespace(decision="PENDING", created_at=now - timedelta(seconds=301), response_json="{}")
    assert is_stale_pending_request(record, max_age_seconds=300, now=now) is True
    assert replay_response(record) is None


def test_pending_request_reconciles_exact_existing_option_trade():
    from datetime import datetime, timezone

    db = make_db()
    signal_data = {
        **signal(),
        "decision": "QUALIFIED",
        "quantity": 75,
        "underlying": {"symbol": "NIFTY", "expiry": "2026-09-24"},
        "contract": {"security_id": "12345", "strike": 25000, "option_type": "CE"},
    }
    record, claimed = claim_request(db, 1, "fno-recovery-001", signal_data)
    assert claimed is True

    trade = PaperTrade(
        user_id=1,
        symbol="NIFTY 2026-09-24 25000 CE",
        side="BUY",
        status="OPEN",
        quantity=75,
        entry_price=120,
        stop_price=90,
        target_price=180,
        strategy_version="V1",
        asset_type="OPTION",
        security_id="12345",
        exchange_segment="NSE_FNO",
        underlying="NIFTY",
        expiry="2026-09-24",
        strike=25000,
        option_type="CE",
        lot_size=75,
        created_at=datetime.now(timezone.utc),
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)

    recovered = reconcile_pending_request(db, record, signal_data)
    assert recovered is not None
    assert recovered["accepted"] is True
    assert recovered["recovered"] is True
    assert recovered["position"]["id"] == trade.id
    db.refresh(record)
    assert record.decision == "ACCEPTED"


def test_pending_request_does_not_reconcile_ambiguous_existing_trades():
    db = make_db()
    signal_data = {
        **signal(),
        "decision": "QUALIFIED",
        "quantity": 75,
        "underlying": {"symbol": "NIFTY", "expiry": "2026-09-24"},
        "contract": {"security_id": "12345", "strike": 25000, "option_type": "CE"},
    }
    record, _ = claim_request(db, 1, "fno-recovery-002", signal_data)
    for _ in range(2):
        db.add(PaperTrade(
            user_id=1, symbol="NIFTY 2026-09-24 25000 CE", side="BUY", status="OPEN",
            quantity=75, entry_price=120, stop_price=90, target_price=180,
            strategy_version="V1", asset_type="OPTION", security_id="12345",
            exchange_segment="NSE_FNO", underlying="NIFTY", expiry="2026-09-24",
            strike=25000, option_type="CE", lot_size=75,
        ))
    db.commit()
    assert reconcile_pending_request(db, record, signal_data) is None
    db.refresh(record)
    assert record.decision == "PENDING"
