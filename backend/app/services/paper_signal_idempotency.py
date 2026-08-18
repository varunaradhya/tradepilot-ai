from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.paper_signal_receipt import PaperSignalReceipt


def build_signal_key(signal: dict[str, Any]) -> str:
    """Build a stable request key when clients do not supply one."""
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


def build_request_fingerprint(signal: dict[str, Any]) -> str:
    return build_signal_key(signal)


def get_receipt(db: Session, user_id: int, idempotency_key: str) -> PaperSignalReceipt | None:
    return (
        db.query(PaperSignalReceipt)
        .filter(
            PaperSignalReceipt.user_id == user_id,
            PaperSignalReceipt.idempotency_key == idempotency_key,
        )
        .first()
    )


def record_receipt(
    db: Session,
    user_id: int,
    *,
    idempotency_key: str,
    signal: dict[str, Any],
    response: dict[str, Any],
) -> PaperSignalReceipt:
    record = PaperSignalReceipt(
        user_id=user_id,
        idempotency_key=idempotency_key,
        session=str(signal["session"]),
        symbol=str(signal["symbol"]).strip().upper(),
        strategy_version=str(signal.get("strategy_version", "V1")),
        interval=str(signal.get("interval", "5")),
        request_fingerprint=build_request_fingerprint(signal),
        accepted=bool(response.get("accepted")),
        response_json=json.dumps(response, sort_keys=True, separators=(",", ":"), default=str),
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = get_receipt(db, user_id, idempotency_key)
        if existing is None:
            raise
        return existing
    db.refresh(record)
    return record


def response_from_receipt(record: PaperSignalReceipt) -> dict[str, Any]:
    return json.loads(record.response_json)
