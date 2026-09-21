from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
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
        "action": str(signal.get("action", signal.get("direction", ""))).upper(),
        "decision": str(signal.get("decision", "")).upper(),
        "entry": signal.get("entry"),
        "stop": signal.get("stop"),
        "target": signal.get("target"),
        "lot_size": signal.get("lot_size", 1),
        "security_id": str((signal.get("contract") or {}).get("security_id", signal.get("security_id", ""))),
        "strike": (signal.get("contract") or {}).get("strike", signal.get("strike")),
        "option_type": str((signal.get("contract") or {}).get("option_type", signal.get("option_type", ""))).upper(),
        "candle_timestamp": signal.get("candle_timestamp", signal.get("bar_timestamp")),
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
        if existing.request_fingerprint != request_fingerprint(signal):
            raise ValueError("paper signal request_id was already used for a different signal")
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
        if existing.request_fingerprint != request_fingerprint(signal):
            raise ValueError("paper signal request_id was already used for a different signal")
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


def pending_request_age_seconds(record: PaperSignalRequest, now: datetime | None = None) -> float:
    """Return age of a PENDING request using UTC-safe timestamp handling."""
    if record.decision != "PENDING":
        return 0.0
    current = now or datetime.now(timezone.utc)
    created = record.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return max(0.0, (current - created.astimezone(timezone.utc)).total_seconds())


def is_stale_pending_request(
    record: PaperSignalRequest,
    *,
    max_age_seconds: float = 300.0,
    now: datetime | None = None,
) -> bool:
    """Identify crash-left PENDING requests without silently retrying them."""
    if max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be positive")
    return record.decision == "PENDING" and pending_request_age_seconds(record, now) > max_age_seconds
