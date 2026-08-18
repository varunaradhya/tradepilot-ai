import pytest

from app.services.paper_backtest_divergence import compare_backtest_to_paper


def test_divergence_stays_within_range_with_sufficient_evidence():
    result = compare_backtest_to_paper(
        {"metrics": {"return_percent": 20.0, "max_drawdown_percent": 8.0}},
        {"summary": {"initial_capital": 100000, "realized_pnl": 15000, "closed_trades": 40, "max_drawdown_percent": 10.0}},
        max_return_gap_percent=10,
        max_drawdown_gap_percent=10,
    )
    assert result["status"] == "WITHIN_EXPECTED_RANGE"
    assert result["live_execution_authorized"] is False
    assert result["warnings"] == []


def test_divergence_warns_on_return_and_drawdown_gap():
    result = compare_backtest_to_paper(
        {"metrics": {"return_percent": 40.0, "max_drawdown_percent": 5.0}},
        {"summary": {"initial_capital": 100000, "realized_pnl": 10000, "closed_trades": 40, "max_drawdown_percent": 20.0}},
    )
    assert result["status"] == "DIVERGENCE_WARNING"
    assert "RETURN_DIVERGENCE" in result["warnings"]
    assert "DRAWDOWN_DIVERGENCE" in result["warnings"]


def test_divergence_requires_minimum_paper_evidence():
    result = compare_backtest_to_paper(
        {"metrics": {"return_percent": 10.0, "max_drawdown_percent": 5.0}},
        {"summary": {"initial_capital": 100000, "realized_pnl": 1000, "closed_trades": 2, "max_drawdown_percent": 5.0}},
    )
    assert "INSUFFICIENT_PAPER_EVIDENCE" in result["warnings"]


def test_divergence_rejects_invalid_thresholds():
    with pytest.raises(ValueError):
        compare_backtest_to_paper({}, {}, max_return_gap_percent=-1)
    with pytest.raises(ValueError):
        compare_backtest_to_paper({}, {}, min_paper_trades=0)
