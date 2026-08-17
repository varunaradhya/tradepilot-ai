from datetime import datetime, timezone

from app.services.market_session import is_cash_session_open, session_date


def test_cash_session_uses_india_timezone():
    # 09:15 IST represented as 03:45 UTC.
    assert is_cash_session_open(datetime(2026, 8, 17, 3, 45, tzinfo=timezone.utc)) is True


def test_cash_session_rejects_weekend():
    assert is_cash_session_open(datetime(2026, 8, 15, 4, 0, tzinfo=timezone.utc)) is False


def test_session_date_normalizes_to_india():
    value = datetime(2026, 8, 17, 20, 0, tzinfo=timezone.utc)
    assert str(session_date(value)) == "2026-08-18"
