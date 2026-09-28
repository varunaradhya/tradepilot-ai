from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.paper_market_state import PaperMarketState


def load_market_state(db: Session, user_id: int, session: str, symbol: str, interval: str = "5", strategy_version: str = "V1") -> dict[str, Any] | None:
    row = db.query(PaperMarketState).filter(
        PaperMarketState.user_id == user_id,
        PaperMarketState.session == session,
        PaperMarketState.symbol == symbol.strip().upper(),
        PaperMarketState.interval == interval,
        PaperMarketState.strategy_version == strategy_version,
    ).first()
    if row is None:
        return None
    try:
        value = json.loads(row.state_json)
    except (TypeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def save_market_state(db: Session, user_id: int, session: str, symbol: str, state: dict[str, Any], interval: str = "5", strategy_version: str = "V1") -> PaperMarketState:
    normalized = symbol.strip().upper()
    row = db.query(PaperMarketState).filter(
        PaperMarketState.user_id == user_id,
        PaperMarketState.session == session,
        PaperMarketState.symbol == normalized,
        PaperMarketState.interval == interval,
        PaperMarketState.strategy_version == strategy_version,
    ).first()
    if row is None:
        row = PaperMarketState(user_id=user_id, session=session, symbol=normalized, interval=interval, strategy_version=strategy_version, state_json=json.dumps(state, separators=(",", ":")))
        db.add(row)
    else:
        row.state_json = json.dumps(state, separators=(",", ":"))
    db.commit()
    db.refresh(row)
    return row


def clear_market_state(db: Session, user_id: int, session: str | None = None, symbol: str | None = None) -> int:
    query = db.query(PaperMarketState).filter(PaperMarketState.user_id == user_id)
    if session:
        query = query.filter(PaperMarketState.session == session)
    if symbol:
        query = query.filter(PaperMarketState.symbol == symbol.strip().upper())
    rows = query.all()
    for row in rows:
        db.delete(row)
    db.commit()
    return len(rows)
