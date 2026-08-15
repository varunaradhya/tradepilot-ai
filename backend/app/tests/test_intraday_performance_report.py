from datetime import datetime, timedelta

from app.services.intraday_backtest import IntradayBacktestConfig
from app.services.intraday_performance_report import build_intraday_performance_report


def _rows():
    start = datetime(2026, 1, 5, 9, 15)
    rows = []
    price = 100.0
    for i in range(60):
        timestamp = start + timedelta(minutes=5 * i)
        session = timestamp.date().isoformat()
        close = price + (0.15 if i > 25 else 0.02)
        rows.append({"timestamp": timestamp, "session": session, "open": price, "high": close + 0.1, "low": price - 0.05, "close": close, "volume": 2000.0})
        price = close
    return rows


def test_performance_report_contains_baseline_cost_stress_and_time_buckets():
    result = build_intraday_performance_report(_rows(), IntradayBacktestConfig())
    assert result["method"].startswith("descriptive performance diagnostics")
    assert "baseline" in result
    assert "cost_stress" in result
    assert "time_of_day" in result
    assert result["cost_stress_return_delta_percent"] <= 0


def test_performance_report_handles_empty_dataset():
    result = build_intraday_performance_report([])
    assert result["baseline"]["trades"] == 0
    assert result["daily"] == {}
    assert result["profitable_days_percent"] == 0.0
