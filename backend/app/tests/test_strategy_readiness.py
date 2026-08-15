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

    trades = [Trade() for _ in range(30)]
    result = build_strategy_readiness(
        {"status": "PAPER_CANDIDATE"},
        {"summary": {"symbols_tested": 5, "robust_percent": 80}},
        trades,
    )
    assert result["status"] == "LIVE_REVIEW"
    assert result["live_trading_allowed"] is False
    assert result["paper"]["trades"] == 30
