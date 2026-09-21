from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.paper_signal_request import PaperSignalRequest
from app.services.paper_signal_request_service import claim_request, complete_request, replay_response, request_fingerprint


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
