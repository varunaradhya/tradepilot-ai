from datetime import date
import pytest
from app.services.nse_equity_calendar import (
    DEFAULT_NSE_EQUITY_CALENDAR,
    NSE_EQUITY_HOLIDAYS_2026,
    expected_nse_equity_sessions,
)

def test_2026_nse_equity_calendar_skips_exchange_holidays():
    assert DEFAULT_NSE_EQUITY_CALENDAR.is_trading_day(date(2026, 10, 1))
    assert not DEFAULT_NSE_EQUITY_CALENDAR.is_trading_day(date(2026, 10, 2))
    assert not DEFAULT_NSE_EQUITY_CALENDAR.is_trading_day(date(2026, 10, 20))
    assert date(2026, 10, 2) in NSE_EQUITY_HOLIDAYS_2026

def test_2026_calendar_does_not_treat_muhurat_as_regular_session():
    assert not DEFAULT_NSE_EQUITY_CALENDAR.is_trading_day(date(2026, 11, 8))

def test_thirty_sessions_are_exchange_sessions_not_weekdays():
    sessions = expected_nse_equity_sessions(date(2026, 9, 28), 30)
    assert len(sessions) == 30
    assert date(2026, 10, 2) not in sessions
    assert date(2026, 10, 20) not in sessions
    assert all(day.weekday() < 5 for day in sessions)

def test_calendar_fails_closed_when_year_not_loaded():
    with pytest.raises(ValueError, match="holiday calendar"):
        expected_nse_equity_sessions(date(2027, 1, 4), 30)
