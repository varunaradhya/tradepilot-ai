from datetime import datetime, timezone, timedelta

from app.services.strategy_readiness import build_strategy_readiness


def test_readiness_blocks_live_and_requires_paper_sample():
    result = build_strategy_readiness(
        {"status": "PAPER_CANDIDATE"},
        {"summary": {"symbols_tested": 5, "robust_percent": 80}},
        [],
    )
    assert result["status"] == "PAPER_VALIDATION"
    assert result["paper_trading_allowed"] is True
    assert result["live_trading_allowed"] is False
    assert result["checks"]["paper_trade_sample"] is False


def test_readiness_rejects_weak_cross_stock_evidence():
    result = build_strategy_readiness(
        {"status": "PAPER_CANDIDATE"},
        {"summary": {"symbols_tested": 5, "robust_percent": 40}},
        [],
    )
    assert result["status"] == "NOT_READY"
    assert result["paper_trading_allowed"] is False
    assert "CROSS_STOCK_EVIDENCE_INSUFFICIENT" in result["reasons"]


def test_readiness_requires_realized_paper_performance_before_live_review():
    class Trade:
        status = "CLOSED"
        pnl = 100.0

    class Loss:
        status = "CLOSED"
        pnl = -100.0

    trades = [Trade() for _ in range(20)] + [Loss() for _ in range(10)]
    result = build_strategy_readiness(
        {"status": "PAPER_CANDIDATE"},
        {"summary": {"symbols_tested": 5, "robust_percent": 80}},
        trades,
    )
    assert result["status"] == "LIVE_REVIEW"
    assert result["live_trading_allowed"] is False
    assert result["paper"]["trades"] == 30
    assert result["paper"]["profit_factor"] == 2.0


def test_readiness_exposes_r_multiple_holding_time_and_exit_distribution():
    class Trade:
        status = "CLOSED"
        pnl = 200.0
        entry_price = 100.0
        stop_price = 90.0
        quantity = 1
        reason = "TARGET"
        created_at = datetime(2026, 8, 15, 9, 15, tzinfo=timezone.utc)
        closed_at = created_at + timedelta(minutes=30)

    result = build_strategy_readiness(
        {"status": "PAPER_CANDIDATE"},
        {"summary": {"symbols_tested": 5, "robust_percent": 80}},
        [Trade()],
    )
    assert result["paper"]["average_r"] == 20.0
    assert result["paper"]["average_hold_minutes"] == 30.0
    assert result["paper"]["max_consecutive_losses"] == 0
    assert result["paper"]["exit_reasons"] == {"TARGET": 1}


def test_readiness_tracks_consecutive_losses_and_stop_distribution():
    class Trade:
        status = "CLOSED"
        entry_price = 100.0
        stop_price = 95.0
        quantity = 1
        reason = "STOP"
        created_at = None
        closed_at = None

    first = Trade(); first.pnl = -10.0
    second = Trade(); second.pnl = -5.0
    third = Trade(); third.pnl = 20.0
    result = build_strategy_readiness(
        {"status": "PAPER_CANDIDATE"},
        {"summary": {"symbols_tested": 5, "robust_percent": 80}},
        [first, second, third],
    )
    assert result["paper"]["max_consecutive_losses"] == 2
    assert result["paper"]["exit_reasons"] == {"STOP": 3}
