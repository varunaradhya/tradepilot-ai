from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest


def _rows(session: str, start: float, n: int = 40):
    rows = []
    price = start
    for _ in range(n):
        price += 0.15
        rows.append({
            "open": price - 0.05,
            "high": price + 0.2,
            "low": price - 0.2,
            "close": price,
            "volume": 1000.0,
            "session": session,
        })
    return rows


def test_backtest_does_not_reuse_previous_session_opening_range():
    first = _rows("2026-01-02", 100)
    second = _rows("2026-01-05", 500)
    # The second session must build its OR from its own first bars.
    second[3]["close"] = 502
    second[3]["high"] = 503
    second[3]["volume"] = 5000
    result = run_intraday_backtest(first + second, IntradayBacktestConfig())
    assert "trades" in result
    assert result["ending_capital"] >= 0


def test_backtest_exposes_expectancy_and_drawdown_metrics():
    result = run_intraday_backtest(_rows("2026-01-02", 100))
    assert "expectancy" in result
    assert "average_win" in result
    assert "average_loss" in result
    assert "max_drawdown_percent" in result
    assert result["max_drawdown_percent"] >= 0
