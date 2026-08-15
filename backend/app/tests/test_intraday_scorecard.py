from datetime import datetime, timedelta

from app.services.intraday_scorecard import build_intraday_scorecard


def _rows(n=80):
    start = datetime(2025, 1, 2, 9, 15)
    return [{"timestamp": start + timedelta(minutes=5*i), "open": 100+i*.1, "high": 101+i*.1, "low": 99+i*.1, "close": 100.5+i*.1, "volume": 1000+i} for i in range(n)]


def test_scorecard_empty():
    assert build_intraday_scorecard({})["status"] == "NO_DATA"


def test_scorecard_ranks_and_exposes_safety_assumptions():
    result = build_intraday_scorecard({"tcs": _rows(), "INFY": _rows()})
    assert result["status"] == "OK"
    assert len(result["ranked"]) == 2
    assert result["assumptions"]["parameter_selection"] is False
    assert all("robustness" in item for item in result["ranked"])
