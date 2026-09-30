from __future__ import annotations

from types import SimpleNamespace

from app.services.paper_reconciliation_service import _orphan_learning_event_ids


def test_open_dhan_trade_learning_event_is_not_orphaned() -> None:
    events = [SimpleNamespace(id=10), SimpleNamespace(id=20)]
    trades = [
        SimpleNamespace(status="OPEN", learning_event_id=10),
        SimpleNamespace(status="CLOSED", learning_event_id=20),
    ]

    assert _orphan_learning_event_ids(events, trades) == []


def test_unlinked_learning_event_is_reported_as_orphan() -> None:
    events = [SimpleNamespace(id=10), SimpleNamespace(id=20)]
    trades = [SimpleNamespace(status="OPEN", learning_event_id=10)]

    assert _orphan_learning_event_ids(events, trades) == [20]
