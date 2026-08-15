from app.services.strategy_qualification import QualificationPolicy, qualify_strategy


def _backtest(**overrides):
    result = {"trades": 100, "profit_factor": 1.4, "max_drawdown_percent": 8.0}
    result.update(overrides)
    return result


def _robustness(**overrides):
    summary = {"positive_return_percent": 80.0, "profit_factor_above_1_percent": 80.0}
    summary.update(overrides)
    return {"summary": summary}


def _wf(**overrides):
    summary = {"success_rate_percent": 70.0}
    summary.update(overrides)
    return {"windows": 10, "v2": {"summary": summary}}


def test_qualifies_only_when_all_research_gates_pass():
    result = qualify_strategy(_backtest(), _robustness(), _wf())
    assert result["status"] == "PAPER_CANDIDATE"
    assert result["paper_trading_allowed"] is True
    assert result["passed_checks"] == result["total_checks"]


def test_low_profit_factor_blocks_paper_candidate():
    result = qualify_strategy(_backtest(profit_factor=1.02), _robustness(), _wf())
    assert result["status"] == "NOT_QUALIFIED"
    assert result["paper_trading_allowed"] is False


def test_missing_walk_forward_blocks_by_default():
    result = qualify_strategy(_backtest(), _robustness(), None)
    assert result["status"] == "NOT_QUALIFIED"
    assert any(check["name"] == "walk_forward" and not check["passed"] for check in result["checks"])


def test_policy_can_require_stricter_drawdown():
    policy = QualificationPolicy(max_drawdown_percent=5.0)
    result = qualify_strategy(_backtest(), _robustness(), _wf(), policy)
    assert result["status"] == "NOT_QUALIFIED"
    assert any(check["name"] == "drawdown" and not check["passed"] for check in result["checks"])
