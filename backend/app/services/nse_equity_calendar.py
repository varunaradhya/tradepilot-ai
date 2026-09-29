from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

# NSE Equity (CM) regular-session holidays. Source: NSE Market Timings & Holidays,
# calendar year 2026. Muhurat Trading on 2026-11-08 is intentionally excluded
# from the regular NSE_EQ validation session calendar.
NSE_EQUITY_HOLIDAYS_2026 = frozenset({
    date(2026, 1, 15), date(2026, 1, 26), date(2026, 3, 3),
    date(2026, 3, 26), date(2026, 3, 31), date(2026, 4, 3),
    date(2026, 4, 14), date(2026, 5, 1), date(2026, 5, 28),
    date(2026, 6, 26), date(2026, 9, 14), date(2026, 10, 2),
    date(2026, 10, 20), date(2026, 11, 10), date(2026, 11, 24),
    date(2026, 12, 25),
})

@dataclass(frozen=True)
class NSEEquityCalendar:
    market: str = "NSE_EQ"
    calendar_year: int = 2026
    source: str = "NSE Market Timings & Holidays"
    source_version: str = "2026-equities"
    holidays: frozenset[date] = NSE_EQUITY_HOLIDAYS_2026
    special_sessions: frozenset[date] = frozenset({date(2026, 11, 8)})

    def is_trading_day(self, day: date) -> bool:
        return day.weekday() < 5 and day not in self.holidays

    def expected_sessions_between(self, start: date, end: date) -> list[date]:
        if end < start:
            raise ValueError("end must not be before start")
        if start.year != self.calendar_year or end.year != self.calendar_year:
            raise ValueError(
                f"{self.market} validation calendar supports {self.calendar_year}; "
                "load the applicable NSE holiday calendar before validating this window"
            )
        sessions: list[date] = []
        current = start
        while current <= end:
            if self.is_trading_day(current):
                sessions.append(current)
            current = date.fromordinal(current.toordinal() + 1)
        return sessions

    def expected_sessions(self, start: date, count: int) -> list[date]:
        if count < 1:
            raise ValueError("count must be positive")
        if start.year != self.calendar_year:
            raise ValueError(
                f"{self.market} validation calendar supports {self.calendar_year}; "
                "load the applicable NSE holiday calendar before starting this run"
            )
        sessions: list[date] = []
        current = start
        while len(sessions) < count:
            if current.year != self.calendar_year:
                raise ValueError(
                    f"validation window crosses beyond {self.calendar_year}; "
                    "load the applicable NSE holiday calendar before continuing"
                )
            if self.is_trading_day(current):
                sessions.append(current)
            current = date.fromordinal(current.toordinal() + 1)
        return sessions

DEFAULT_NSE_EQUITY_CALENDAR = NSEEquityCalendar()

def expected_nse_equity_sessions(start: date, count: int = 30, calendar: NSEEquityCalendar = DEFAULT_NSE_EQUITY_CALENDAR) -> list[date]:
    return calendar.expected_sessions(start, count)

def nse_equity_holidays(year: int = 2026) -> frozenset[date]:
    if year != 2026:
        raise ValueError(f"NSE equity holiday calendar not loaded for {year}")
    return NSE_EQUITY_HOLIDAYS_2026
