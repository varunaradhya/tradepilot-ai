from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

NSE_EQUITY_HOLIDAYS_2026 = frozenset({
    date(2026, 1, 15), date(2026, 1, 26), date(2026, 3, 3),
    date(2026, 3, 26), date(2026, 3, 31), date(2026, 4, 3),
    date(2026, 4, 14), date(2026, 5, 1), date(2026, 5, 28),
    date(2026, 6, 26), date(2026, 9, 14), date(2026, 10, 2),
    date(2026, 10, 20), date(2026, 11, 10), date(2026, 11, 24),
    date(2026, 12, 25),
})

REGULAR_OPEN = time(9, 15)
REGULAR_CLOSE = time(15, 30)

@dataclass(frozen=True)
class NSESessionWindow:
    start: time
    end: time

@dataclass(frozen=True)
class NSESessionClassification:
    status: str
    windows: tuple[NSESessionWindow, ...] = ()
    reason: str = ""

# These exceptional dates are source-backed against the NSE circulars captured
# in docs/REAL_DATA_VALIDATION_2026-10-01.md. Mock sessions are never researchable.
NSE_SPECIAL_SESSION_WINDOWS = {
    date(2023, 11, 12): (NSESessionWindow(time(18, 15), time(19, 15)),),
    date(2024, 1, 20): (NSESessionWindow(REGULAR_OPEN, REGULAR_CLOSE),),
    date(2024, 3, 2): (
        NSESessionWindow(time(9, 15), time(10, 0)),
        NSESessionWindow(time(11, 30), time(12, 30)),
    ),
    date(2024, 5, 18): (
        NSESessionWindow(time(9, 15), time(10, 0)),
        NSESessionWindow(time(11, 30), time(12, 30)),
    ),
    date(2025, 2, 1): (NSESessionWindow(REGULAR_OPEN, REGULAR_CLOSE),),
    date(2026, 2, 1): (NSESessionWindow(REGULAR_OPEN, REGULAR_CLOSE),),
}

NSE_MOCK_SESSION_DATES = frozenset({
    date(2022, 4, 9),
    date(2022, 4, 30),
})

@dataclass(frozen=True)
class NSEEquityCalendar:
    market: str = "NSE_EQ"
    calendar_year: int = 2026
    source: str = "NSE Market Timings & Holidays + validated exceptional sessions"
    source_version: str = "2026-equities+validated-exceptions-2026-10-01"
    holidays: frozenset[date] = NSE_EQUITY_HOLIDAYS_2026
    special_sessions: frozenset[date] = frozenset(NSE_SPECIAL_SESSION_WINDOWS)

    def is_trading_day(self, day: date) -> bool:
        return day.weekday() < 5 and day not in self.holidays

    def classify_session(self, day: date) -> NSESessionClassification:
        if day in NSE_MOCK_SESSION_DATES:
            return NSESessionClassification("MOCK", reason="NSE-documented mock trading session")
        if day in NSE_SPECIAL_SESSION_WINDOWS:
            return NSESessionClassification(
                "LIVE_SPECIAL",
                windows=NSE_SPECIAL_SESSION_WINDOWS[day],
                reason="NSE-documented live/special trading session",
            )
        if day.weekday() >= 5:
            return NSESessionClassification(
                "UNKNOWN",
                reason="Weekend date without a source-backed live-session classification",
            )
        if day in self.holidays:
            return NSESessionClassification("HOLIDAY", reason="NSE regular-session holiday")
        return NSESessionClassification(
            "REGULAR",
            windows=(NSESessionWindow(REGULAR_OPEN, REGULAR_CLOSE),),
            reason="Regular NSE equity weekday session",
        )

    @staticmethod
    def is_timestamp_in_session(
        timestamp_time: time,
        classification: NSESessionClassification,
    ) -> bool:
        return any(
            window.start <= timestamp_time <= window.end
            for window in classification.windows
        )

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

def expected_nse_equity_sessions(
    start: date,
    count: int = 30,
    calendar: NSEEquityCalendar = DEFAULT_NSE_EQUITY_CALENDAR,
) -> list[date]:
    return calendar.expected_sessions(start, count)

def nse_equity_holidays(year: int = 2026) -> frozenset[date]:
    if year != 2026:
        raise ValueError(f"NSE equity holiday calendar not loaded for {year}")
    return NSE_EQUITY_HOLIDAYS_2026
