from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.services.strict_session_certification import certify_nse_five_minute_session, summarize_certifications


def _rows(session_date: date, *, terminal: bool = False):
    start = datetime.combine(session_date, time(9, 15), tzinfo=ZoneInfo("Asia/Kolkata"))
    count = 75 + int(terminal)
    return [
        {
            "timestamp": (start + timedelta(minutes=5 * index)).isoformat(),
            "open": 100 + index * 0.01,
            "high": 101 + index * 0.01,
            "low": 99 + index * 0.01,
            "close": 100.5 + index * 0.01,
            "volume": 1000,
        }
        for index in range(count)
    ]


def test_certifies_exact_nse_five_minute_grid():
    session_date = date(2026, 1, 5)
    result = certify_nse_five_minute_session(symbol="TCS", session_date=session_date, rows=_rows(session_date))
    assert result["classification"] == "STRICT_VALID"
    assert result["interval_validation"]["exact_clock_grid"] is True
    assert result["content_fingerprint"] == result["dataset_fingerprint"]
    assert result["corporate_action_state"] == "UNKNOWN"


def test_rejects_irregular_raw_timestamp_without_repairing_it():
    session_date = date(2026, 1, 5)
    rows = _rows(session_date)
    rows[12]["timestamp"] = (datetime.fromisoformat(rows[12]["timestamp"]) + timedelta(minutes=1)).isoformat()
    result = certify_nse_five_minute_session(symbol="TCS", session_date=session_date, rows=rows)
    assert result["classification"] == "INVALID"
    assert result["interval_validation"]["exact_clock_grid"] is False
    assert result["interval_validation"]["observed_delta_counts"][240] == 1
    assert result["interval_validation"]["observed_delta_counts"][360] == 1


def test_accepts_documented_terminal_observation_and_summarizes_results():
    session_date = date(2026, 1, 5)
    strict = certify_nse_five_minute_session(symbol="TCS", session_date=session_date, rows=_rows(session_date, terminal=True))
    invalid = {**strict, "classification": "INVALID", "symbol": "INFY"}
    summary = summarize_certifications([strict, invalid])
    assert strict["classification"] == "STRICT_VALID"
    assert summary["strict_valid_sessions"] == 1
    assert summary["invalid_sessions"] == 1
