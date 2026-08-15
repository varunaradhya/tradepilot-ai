from app.services.paper_readiness import PaperReadinessPolicy, evaluate_paper_readiness


def _good_metrics():
    return {
        "trades": 250,
        "profit_factor": 1.55,
        "expectancy": 75.0,
        "max_drawdown_percent": 7.5,
        "lookahead_bias_protection": True,
    }


def test_strong_evidence_can_pass_paper_gate():
    result = evaluate_paper_readiness(
        _good_metrics(),
        [{"return_percent": 3.0}, {"return_percent": -1.0}, {"return_percent": 2.0}, {"return_percent": 1.0}],
    )
    assert result["status"] == "PAPER_READY"
    assert result["paper_trading_allowed"] is True


def test_missing_walk_forward_evidence_fails_closed():
    result = evaluate_paper_readiness(_good_metrics(), None)
    assert result["status"] == "NOT_READY"
    assert result["paper_trading_allowed"] is False
    assert result["checks"]["walk_forward"] is False


def test_weak_profit_factor_blocks_paper_trading():
    metrics = {**_good_metrics(), "profit_factor": 1.05}
    result = evaluate_paper_readiness(metrics, [{"return_percent": 1.0}] * 5)
    assert result["paper_trading_allowed"] is False


def test_high_drawdown_blocks_paper_trading():
    metrics = {**_good_metrics(), "max_drawdown_percent": 12.0}
    result = evaluate_paper_readiness(metrics, [{"return_percent": 1.0}] * 5)
    assert result["paper_trading_allowed"] is False


def test_lookahead_protection_is_mandatory_by_default():
    metrics = {**_good_metrics(), "lookahead_bias_protection": False}
    result = evaluate_paper_readiness(metrics, [{"return_percent": 1.0}] * 5)
    assert result["checks"]["lookahead_protection"] is False
    assert result["paper_trading_allowed"] is False


def test_custom_policy_can_raise_the_bar():
    policy = PaperReadinessPolicy(min_trades=500, min_profit_factor=1.8)
    result = evaluate_paper_readiness(_good_metrics(), [{"return_percent": 1.0}] * 10, policy)
    assert result["paper_trading_allowed"] is False


def test_walk_forward_ratio_is_reported():
    result = evaluate_paper_readiness(
        _good_metrics(),
        [{"return_percent": 1.0}, {"return_percent": -1.0}, {"return_percent": 2.0}],
    )
    assert result["walk_forward_positive_ratio"] == 0.6667


def test_empty_walk_forward_fails_closed():
    result = evaluate_paper_readiness(_good_metrics(), [])
    assert result["checks"]["walk_forward"] is False
    assert result["paper_trading_allowed"] is False
