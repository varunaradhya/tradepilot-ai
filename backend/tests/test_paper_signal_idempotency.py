import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.models.paper_signal_request import PaperSignalRequest
from app.services.paper_signal_request_service import (
    claim_request,
    complete_request,
    replay_response,
    request_fingerprint,
)


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[PaperSignalRequest.__table__])
    return Session(engine)


def signal(**overrides):
    value = {
        "session": "2026-08-18",
        "symbol": "RELIANCE",
        "interval": "5",
        "strategy_version": "V1",
        "action": "BUY",
        "entry": 100.0,
        "stop": 98.0,
        "target": 104.0,
        "lot_size": 1,
    }
    value.update(overrides)
    return value


def test_claim_is_idempotent_and_persists_the_fingerprint():
    db = make_session()
    first, owner = claim_request(db, 7, "req-1", signal())
    second, second_owner = claim_request(db, 7, "req-1", signal())

    assert owner is True
    assert second_owner is False
    assert second.id == first.id
    assert first.decision == "PENDING"
    assert first.request_fingerprint == request_fingerprint(signal())


def test_reusing_request_id_for_a_different_signal_is_detectable():
    db = make_session()
    first, owner = claim_request(db, 7, "req-1", signal())
    second_signal = signal(entry=101.0)
    second, second_owner = claim_request(db, 7, "req-1", second_signal)

    assert owner is True
    assert second_owner is False
    assert first.request_fingerprint != request_fingerprint(second_signal)
    assert second.request_fingerprint == first.request_fingerprint


def test_completed_request_replays_exact_response_without_reexecution():
    db = make_session()
    record, owner = claim_request(db, 7, "req-1", signal())
    assert owner is True

    response = {"mode": "SIMULATION_ONLY", "accepted": True, "reason": "PAPER_ORDER_OPENED", "trade_id": 42}
    complete_request(db, record, response)

    stored = db.get(PaperSignalRequest, record.id)
    replay = replay_response(stored)
    assert stored.decision == "ACCEPTED"
    assert replay == response
    assert json.loads(stored.response_json) == response
