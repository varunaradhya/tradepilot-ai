from datetime import datetime, timedelta, timezone

from app.models.paper_trade import PaperTrade
from app.services.strategy_readiness_gate import StrategyReadinessPolicy, evaluate_strategy_readiness


def _trade(index: int, pnl: float, now: datetime, stop: float = 99.0) -> PaperTrade:
    created = now - timedelta(days=20) + timedelta(hours=index)
    return PaperTrade(
        user_id=1,
        symbol="TCS",
        side="BUY",
        status="CLOSED",
        quantity=10,
        entry_price=100.0,
        stop_price=stop,
        target_price=105.0,
        exit_price=100.0 + pnl / 10.0,
        pnl=pnl,
        reason="TARGET" if pnl > 0 else "STOP",
        strategy_version="V1",
        created_at=created,
        closed_at=created + timedelta(minutes=30),
    )


def _common(now: datetime):
    trades = [_trade(i, 20.0, now) for i in range(30)]
    return dict(
        backtest={"strategy_fingerprint": "fingerprint-123", "return_percent": 12.0, "max_drawdown_percent": 3.0, "trades": 100, "profit_factor": 1.8},
        research_qualification={"status": "PAPER_CANDIDATE"},
        cross_stock_evidence={"summary": {"robust_percent": 80.0, "symbols_tested": 5}},
        paper_trades=trades,
        authorized_fingerprint="fingerprint-123",
        reference_now=now,
    )


def test_readiness_requires_full_evidence_and_never_authorizes_live():
    now = datetime.now(timezone.utc)
    result = evaluate_strategy_readiness(**_common(now))
    assert result["status"] == "READY_FOR_STRATEGY_REVIEW"
    assert result["strategy_readiness"] is True
    assert result["live_trading_allowed"] is False
    assert result["promotion"]["strategy_review_to_live"] is False


def test_insufficient_paper_sample_fails_closed():
    now = datetime.now(timezone.utc)
    data = _common(now)
    data["paper_trades"] = data["paper_trades"][:29]
    result = evaluate_strategy_readiness(**data)
    assert result["status"] == "NOT_READY"
    assert "PAPER_SAMPLE_FAILED" in result["reasons"]


def test_fingerprint_drift_blocks_readiness():
    now = datetime.now(timezone.utc)
    data = _common(now)
    data["authorized_fingerprint"] = "old-fingerprint"
    result = evaluate_strategy_readiness(**data)
    assert result["status"] == "NOT_READY"
    assert "PARAMETER_FINGERPRINT_STABLE_FAILED" in result["reasons"]


def test_large_loss_streak_blocks_readiness():
    now = datetime.now(timezone.utc)
    data = _common(now)
    data["paper_trades"] = [_trade(i, -20.0 if i < 6 else 20.0, now) for i in range(30)]
    result = evaluate_strategy_readiness(**data)
    assert result["status"] == "NOT_READY"
    assert "LOSS_STREAK_FAILED" in result["reasons"]


def test_stale_evidence_blocks_readiness():
    now = datetime.now(timezone.utc)
    data = _common(now)
    data["paper_trades"] = [_trade(i, 20.0, now - timedelta(days=45)) for i in range(30)]
    result = evaluate_strategy_readiness(**data, policy=StrategyReadinessPolicy(evidence_max_age_days=30))
    assert result["status"] == "NOT_READY"
    assert "EVIDENCE_FRESHNESS_FAILED" in result["reasons"]


def test_return_divergence_blocks_readiness():
    now = datetime.now(timezone.utc)
    data = _common(now)
    data["backtest"]["return_percent"] = 50.0
    result = evaluate_strategy_readiness(**data)
    assert result["status"] == "NOT_READY"
    assert "BACKTEST_PAPER_DIVERGENCE_FAILED" in result["reasons"]
