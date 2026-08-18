from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.paper_session_state import PaperSessionState


def load_paper_session_state(db: Session, user_id: int) -> dict[str, Any] | None:
    record = db.query(PaperSessionState).filter(PaperSessionState.user_id == user_id).first()
    if record is None:
        return None
    try:
        value = json.loads(record.state_json)
    except (TypeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def save_paper_session_state(db: Session, user_id: int, state: dict[str, Any]) -> PaperSessionState:
    record = db.query(PaperSessionState).filter(PaperSessionState.user_id == user_id).first()
    encoded = json.dumps(state, sort_keys=True, separators=(",", ":"), default=str)
    if record is None:
        record = PaperSessionState(user_id=user_id, state_json=encoded)
        db.add(record)
    else:
        record.state_json = encoded
        record.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return record
