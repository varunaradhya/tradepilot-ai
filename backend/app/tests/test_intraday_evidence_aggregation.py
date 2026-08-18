from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services.intraday_evidence_aggregation import aggregate_paper_performance, aggregate_scorecards


def test_aggregate_scorecards_reports_missing_and_robust_share():
    result = aggregate_scorecards(
        [
            {"symbol": "TCS", "score": 80, "metrics": {"return_percent": 5, "profit_factor": 1.5, "max_drawdown_percent": 4}, "robustness": {"status": "ROBUST"}},
            {"symbol": "INFY", "score": 60, "metrics": {"return_percent": -1, "profit_factor": 0.9, "max_drawdown_percent": 8}, "robustness": {"status": "NEEDS_REVIEW"}},
        ],
        interval="5",
        requested_symbols=["TCS", "INFY", "SBIN"],
        missing_symbols=["SBIN"],
    )
    assert result["summary"]["symbols_tested"] == 2
    assert result["summary"]["robust_percent"] == 50.0
    assert result["missing_symbols"] == ["SBIN"]
    assert result["research_policy"]["cross_stock_optimization"] is False


def test_aggregate_scorecards_empty_is_explicit():
    result = aggregate_scorecards([], interval="5", requested_symbols=["TCS"], missing_symbols=["TCS"])
    assert result["status"] == "NO_DATA"
    assert result["summary"]["symbols_tested"] == 0


def test_aggregate_paper_performance_groups_symbols_and_exit_reasons():
    now = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
    trades = [
        SimpleNamespace(symbol="TCS", status="CLOSED", pnl=100.0, reason="TARGET", created_at=now, closed_at=now),
        SimpleNamespace(symbol="TCS", status="CLOSED", pnl=-50.0, reason="STOP", created_at=now, closed_at=now),
        SimpleNamespace(symbol="INFY", status="OPEN", pnl=0.0, reason=None, created_at=now, closed_at=None),
    ]
    result = aggregate_paper_performance(trades)
    assert result["mode"] == "SIMULATION_ONLY"
    assert result["initial_capital"] == 100000.0
    assert result["summary"]["realized_pnl"] == 50.0
    assert result["summary"]["profit_factor"] == 2.0
    assert result["summary"]["max_consecutive_losses"] == 1
    assert result["summary"]["profitable_days"] == 1
    assert result["summary"]["trading_days"] == 1
    assert result["daily"] == [{"date": "2026-01-02", "pnl": 50.0}]
    assert result["by_symbol"]["TCS"]["win_rate_percent"] == 50.0
    assert result["exit_reasons"] == {"STOP": 1, "TARGET": 1}


def test_paper_drawdown_is_independent_of_database_return_order():
    start = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
    later = start + timedelta(minutes=5)
    trades = [
        SimpleNamespace(symbol="TCS", status="CLOSED", pnl=-900.0, reason="STOP", created_at=later, closed_at=later),
        SimpleNamespace(symbol="TCS", status="CLOSED", pnl=2000.0, reason="TARGET", created_at=start, closed_at=start),
    ]
    result = aggregate_paper_performance(trades, initial_capital=10000.0)
    # Correct chronological equity: 10,000 -> 12,000 -> 11,100 = 7.5% drawdown.
    assert result["summary"]["max_drawdown_percent"] == 7.5


def test_paper_evidence_uses_supplied_initial_capital():
    now = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
    trade = SimpleNamespace(symbol="TCS", status="CLOSED", pnl=-500.0, reason="STOP", created_at=now, closed_at=now)
    result = aggregate_paper_performance([trade], initial_capital=5000.0)
    assert result["initial_capital"] == 5000.0
    assert result["summary"]["max_drawdown_percent"] == 10.0


def test_paper_evidence_rejects_invalid_initial_capital():
    with pytest.raises(ValueError):
        aggregate_paper_performance([], initial_capital=0)
    with pytest.raises(ValueError):
        aggregate_paper_performance([], initial_capital=-1)


def test_aggregate_paper_performance_empty():
    result = aggregate_paper_performance([])
    assert result["summary"]["closed_trades"] == 0
    assert result["summary"]["profit_factor"] is None
    assert result["summary"]["max_drawdown_percent"] == 0.0
    assert result["by_symbol"] == {}
    assert result["daily"] == []
