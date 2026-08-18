from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.paper_signal_request import PaperSignalRequest


def request_fingerprint(signal: dict[str, Any]) -> str:
    canonical = {
        "session": str(signal.get("session", "")),
        "symbol": str(signal.get("symbol", "")).strip().upper(),
        "interval": str(signal.get("interval", "5")),
        "strategy_version": str(signal.get("strategy_version", "V1")),
        "action": str(signal.get("action", "")).upper(),
        "entry": signal.get("entry"),
        "stop": signal.get("stop"),
        "target": signal.get("target"),
        "lot_size": signal.get("lot_size", 1),
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def get_request(db: Session, user_id: int, request_id: str) -> PaperSignalRequest | None:
    return (
        db.query(PaperSignalRequest)
        .filter(
            PaperSignalRequest.user_id == user_id,
            PaperSignalRequest.request_id == request_id,
        )
        .first()
    )


def claim_request(
    db: Session,
    user_id: int,
    request_id: str,
    signal: dict[str, Any],
) -> tuple[PaperSignalRequest, bool]:
    existing = get_request(db, user_id, request_id)
    if existing is not None:
        return existing, False

    record = PaperSignalRequest(
        user_id=user_id,
        request_id=request_id,
        symbol=str(signal["symbol"]).strip().upper(),
        strategy_version=str(signal.get("strategy_version", "V1")),
        interval=str(signal.get("interval", "5")),
        session=str(signal["session"]),
        decision="PENDING",
        request_fingerprint=request_fingerprint(signal),
        response_json="{}",
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = get_request(db, user_id, request_id)
        if existing is None:
            raise
        return existing, False
    db.refresh(record)
    return record, True


def complete_request(db: Session, record: PaperSignalRequest, response: dict[str, Any]) -> PaperSignalRequest:
    record.decision = "ACCEPTED" if response.get("accepted") else "REJECTED"
    record.response_json = json.dumps(response, sort_keys=True, separators=(",", ":"), default=str)
    db.commit()
    db.refresh(record)
    return record


def replay_response(record: PaperSignalRequest) -> dict[str, Any] | None:
    if record.decision == "PENDING":
        return None
    return json.loads(record.response_json)
