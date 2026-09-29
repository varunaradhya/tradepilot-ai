from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.paper_trade import PaperTrade
from app.models.paper_trade_learning import PaperTradeLearningEvent


def reconcile_paper_learning(db: Session, user_id: int) -> dict:
    """Check that every closed Dhan paper trade has a durable learning-event link."""
    trades = db.query(PaperTrade).filter(
        PaperTrade.user_id == user_id,
        PaperTrade.status == "CLOSED",
        PaperTrade.reason.like("DHAN:%"),
    ).all()
    events = db.query(PaperTradeLearningEvent).filter(
        PaperTradeLearningEvent.user_id == user_id,
    ).all()
    event_ids = {event.id for event in events}
    unlinked = [trade.id for trade in trades if trade.learning_event_id is None]
    broken = [trade.id for trade in trades if trade.learning_event_id is not None and trade.learning_event_id not in event_ids]
    linked = len(trades) - len(unlinked) - len(broken)
    return {
        "user_id": user_id,
        "closed_dhan_trades": len(trades),
        "learning_events": len(events),
        "linked_trades": linked,
        "unlinked_trade_ids": unlinked,
        "broken_link_trade_ids": broken,
        "reconciled": not unlinked and not broken,
        "evidence_is_descriptive": True,
        "live_execution_enabled": False,
    }
