from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.operational_audit_event import OperationalAuditEvent


def record_event(db: Session, event_type: str, *, severity: str = "INFO", user_id: int | None = None, payload: dict | None = None) -> OperationalAuditEvent:
    event = OperationalAuditEvent(
        event_type=event_type[:80],
        severity=severity[:20].upper(),
        user_id=user_id,
        payload_json=json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), default=str),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_recent_events(db: Session, *, limit: int = 50) -> list[dict]:
    limit = max(1, min(limit, 200))
    events = db.query(OperationalAuditEvent).order_by(OperationalAuditEvent.created_at.desc()).limit(limit).all()
    result = []
    for event in events:
        try:
            payload = json.loads(event.payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        result.append({
            "id": event.id,
            "event_type": event.event_type,
            "severity": event.severity,
            "user_id": event.user_id,
            "payload": payload,
            "created_at": event.created_at.isoformat(),
        })
    return result


def purge_events(db: Session, *, retention_days: int = 90) -> int:
    if retention_days < 1:
        raise ValueError("retention_days must be positive")
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    deleted = db.query(OperationalAuditEvent).filter(OperationalAuditEvent.created_at < cutoff).delete(synchronize_session=False)
    db.commit()
    return int(deleted)
