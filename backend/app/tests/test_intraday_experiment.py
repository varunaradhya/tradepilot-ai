from datetime import datetime

from app.services.intraday_experiment import run_intraday_experiment


def test_empty_experiment_is_safe():
    result = run_intraday_experiment([])
    assert result["status"] == "NO_DATA"


def test_experiment_reports_each_calendar_year():
    rows = []
    for year in (2024, 2025):
        for i in range(5):
            price = 100 + i
            rows.append({
                "timestamp": datetime(year, 1, 2, 9, 15 + i),
                "open": price,
                "high": price + 1,
                "low": price - 1,
                "close": price + 0.5,
                "volume": 1000,
            })
    result = run_intraday_experiment(rows)
    assert result["status"] == "OK"
    assert [item["year"] for item in result["years"]] == [2024, 2025]
    assert result["lookahead_bias_protection"] is True
