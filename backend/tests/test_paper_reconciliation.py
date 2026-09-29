from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.models.paper_trade import PaperTrade
from app.models.paper_trade_learning import PaperTradeLearningEvent
from app.services.paper_reconciliation_service import reconcile_paper_learning


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[PaperTradeLearningEvent.__table__, PaperTrade.__table__])
    return Session(engine)


def test_reconciliation_detects_unlinked_trade():
    db = _db()
    trade = PaperTrade(
        user_id=1, symbol="TCS", side="BUY", status="CLOSED",
        quantity=1, entry_price=100.0, stop_price=99.0, target_price=102.0,
        exit_price=102.0, pnl=2.0, reason="DHAN:2026-01-01:5",
        strategy_version="V1", asset_type="EQUITY",
    )
    db.add(trade)
    db.commit()
    result = reconcile_paper_learning(db, 1)
    assert result["reconciled"] is False
    assert result["unlinked_trade_ids"] == [trade.id]


def test_reconciliation_accepts_linked_trade():
    db = _db()
    event = PaperTradeLearningEvent(
        user_id=1, symbol="TCS", session="2026-01-01", strategy_version="V1",
        model_version="RULES_V1", fingerprint="a" * 64,
        features_json="{}", label=1, pnl=2.0, r_multiple=2.0,
        exit_reason="TARGET",
    )
    db.add(event)
    db.flush()
    trade = PaperTrade(
        user_id=1, symbol="TCS", side="BUY", status="CLOSED",
        learning_event_id=event.id, quantity=1, entry_price=100.0,
        stop_price=99.0, target_price=102.0, exit_price=102.0, pnl=2.0,
        reason="DHAN:2026-01-01:5", strategy_version="V1", asset_type="EQUITY",
    )
    db.add(trade)
    db.commit()
    result = reconcile_paper_learning(db, 1)
    assert result["reconciled"] is True
    assert result["linked_trades"] == 1
