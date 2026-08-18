from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.operational_kill_switch import OperationalKillSwitch


DEFAULT_REASON = "FAIL_CLOSED_DEFAULT"


def get_kill_switch(db: Session) -> OperationalKillSwitch:
    record = db.query(OperationalKillSwitch).filter(OperationalKillSwitch.id == 1).first()
    if record is None:
        record = OperationalKillSwitch(
            id=1,
            active=True,
            reason=DEFAULT_REASON,
            metadata_json="{}",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
    return record


def activate_kill_switch(
    db: Session,
    *,
    reason: str,
    user_id: int | None = None,
    metadata: dict | None = None,
) -> OperationalKillSwitch:
    clean_reason = reason.strip()
    if not clean_reason:
        raise ValueError("Kill-switch reason is required")
    record = get_kill_switch(db)
    record.active = True
    record.reason = clean_reason[:255]
    record.activated_by_user_id = user_id
    record.updated_at = datetime.now(timezone.utc)
    record.metadata_json = json.dumps(metadata or {}, sort_keys=True, separators=(",", ":"), default=str)
    db.commit()
    db.refresh(record)
    return record


def kill_switch_status(db: Session) -> dict:
    record = get_kill_switch(db)
    return {
        "active": bool(record.active),
        "reason": record.reason,
        "activated_by_user_id": record.activated_by_user_id,
        "updated_at": record.updated_at.isoformat(),
        "metadata": json.loads(record.metadata_json or "{}"),
    }
