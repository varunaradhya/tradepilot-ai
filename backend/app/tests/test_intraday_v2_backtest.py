from app.services.intraday_v2_backtest import run_intraday_v2_backtest


def test_v2_backtest_is_safe_on_empty_data():
    result = run_intraday_v2_backtest([])
    assert result["trades"] == 0
    assert result["return_percent"] == 0.0


def test_v2_backtest_reports_standard_metrics():
    rows = []
    for i in range(45):
        p = 100 + i * 0.25
        rows.append({"open": p - 0.05, "high": p + 0.25, "low": p - 0.2, "close": p, "volume": 1000.0, "session": "2026-01-02"})
    result = run_intraday_v2_backtest(rows, rows, rows)
    assert "win_rate_percent" in result
    assert "profit_factor" in result
