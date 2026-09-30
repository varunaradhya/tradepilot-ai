from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.paper_ml_service import _chronological_event_times


def _event(seconds: int) -> SimpleNamespace:
    return SimpleNamespace(event_at=datetime.fromtimestamp(seconds, tz=timezone.utc))


def test_ml_event_chronology_allows_same_timestamp_with_stable_query_tie_break() -> None:
    assert _chronological_event_times([_event(100), _event(100), _event(200)])


def test_ml_event_chronology_rejects_backwards_time() -> None:
    assert not _chronological_event_times([_event(200), _event(100)])
