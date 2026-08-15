from datetime import datetime, timedelta

from app.services.intraday_research_lab import run_research_lab


def _rows(n=40):
    start = datetime(2025, 1, 2, 9, 15)
    rows = []
    for i in range(n):
        p = 100 + i * 0.2
        rows.append({"timestamp": start + timedelta(minutes=5 * i), "open": p, "high": p + 1, "low": p - 1, "close": p + .5, "volume": 1000 + i * 10, "session": "2025-01-02"})
    return rows


def test_lab_empty_is_safe():
    assert run_research_lab([])["status"] == "NO_DATA"


def test_lab_reports_slippage_and_time_windows():
    result = run_research_lab(_rows())
    assert result["status"] == "OK"
    assert len(result["slippage_sensitivity"]) == 5
    assert result["method"] == "diagnostic_only_no_parameter_selection"
    assert result["time_of_day"]
