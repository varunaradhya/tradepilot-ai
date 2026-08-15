from app.services.strategy_evidence import build_strategy_evidence, regime_scorecard


def _trades(values, regime="TRENDING_UP"):
    return [{"pnl": value, "regime": regime} for value in values]


def test_evidence_preserves_strategy_identity():
    result = build_strategy_evidence(
        _trades([10, -5]), _trades([8, -4]), _trades([9, -3]),
        strategy_version="V1", fingerprint="abc123",
    )
    assert result["strategy_version"] == "V1"
    assert result["fingerprint"] == "abc123"


def test_evidence_reports_stage_trade_counts():
    result = build_strategy_evidence(
        _trades([10, -5, 4]), _trades([8, -4]), _trades([9]),
        strategy_version="V1", fingerprint="x",
    )
    assert result["stages"]["backtest"]["trades"] == 3
    assert result["stages"]["oos"]["trades"] == 2
    assert result["stages"]["paper"]["trades"] == 1


def test_evidence_marks_missing_stage_as_incomplete():
    result = build_strategy_evidence(_trades([1]), [], _trades([1]), strategy_version="V1", fingerprint="x")
    assert result["evidence_complete"] is False


def test_evidence_marks_all_present_stages_complete():
    result = build_strategy_evidence(_trades([1]), _trades([1]), _trades([1]), strategy_version="V1", fingerprint="x")
    assert result["evidence_complete"] is True


def test_evidence_detects_severe_pf_degradation():
    result = build_strategy_evidence(
        _trades([100, -10]), _trades([20, -20]), _trades([5, -20]),
        strategy_version="V1", fingerprint="x",
    )
    assert result["interpretation"] == "EDGE_DEGRADING"
    assert result["degradation"]["backtest_to_oos_pf_percent"] < -25


def test_evidence_detects_moderate_degradation():
    result = build_strategy_evidence(
        _trades([100, -50]), _trades([90, -50]), _trades([85, -50]),
        strategy_version="V1", fingerprint="x",
    )
    assert result["interpretation"] == "MONITOR_DEGRADATION"


def test_evidence_reports_insufficient_data_without_pf_comparison():
    result = build_strategy_evidence([], [], [], strategy_version="V1", fingerprint="x")
    assert result["interpretation"] == "INSUFFICIENT_EVIDENCE"


def test_evidence_can_attach_robustness_without_modifying_it():
    robustness = {"status": "PASS", "symbols": 8}
    result = build_strategy_evidence(_trades([2]), _trades([2]), _trades([2]), strategy_version="V1", fingerprint="x", robustness=robustness)
    assert result["robustness"] == robustness


def test_regime_scorecard_separates_market_regimes():
    trades = _trades([10, -5], "TRENDING_UP") + _trades([3, -2], "SIDEWAYS") + _trades([-4], "TRENDING_DOWN")
    result = regime_scorecard(trades)
    assert result["TRENDING_UP"]["trades"] == 2
    assert result["SIDEWAYS"]["trades"] == 2
    assert result["TRENDING_DOWN"]["trades"] == 1


def test_regime_scorecard_keeps_empty_regime_safe():
    result = regime_scorecard(_trades([1], "TRENDING_UP"))
    assert result["SIDEWAYS"]["trades"] == 0
    assert result["SIDEWAYS"]["profit_factor"] is None


def test_regime_scorecard_reports_net_pnl():
    result = regime_scorecard(_trades([10, -4], "TRENDING_UP"))
    assert result["TRENDING_UP"]["net_pnl"] == 6
    assert result["TRENDING_UP"]["average_pnl"] == 3


def test_evidence_uses_fixed_identity_not_parameter_selection():
    result = build_strategy_evidence(_trades([10]), _trades([9]), _trades([8]), strategy_version="V2", fingerprint="fixed-fp")
    assert "selection_policy" not in result
    assert result["fingerprint"] == "fixed-fp"


def test_evidence_degradation_is_bounded_and_explicit():
    result = build_strategy_evidence(_trades([100, -20]), _trades([90, -20]), _trades([80, -20]), strategy_version="V1", fingerprint="x")
    assert isinstance(result["degradation"]["backtest_to_oos_pf_percent"], float)
    assert "interpretation" in result
