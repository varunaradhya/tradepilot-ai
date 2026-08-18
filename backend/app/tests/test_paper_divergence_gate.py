from app.services.paper_divergence_gate import PaperDivergenceConfig, evaluate_backtest_vs_paper


def test_divergence_gate_passes_stable_paper_evidence():
    result = evaluate_backtest_vs_paper(
        {"profit_factor": 1.8, "expectancy": 100, "max_drawdown_percent": 10},
        {"trades": 40, "profit_factor": 1.5, "expectancy": 75, "max_drawdown_percent": 13},
    )
    assert result["status"] == "PASS"


def test_divergence_gate_rejects_material_profit_factor_degradation():
    result = evaluate_backtest_vs_paper(
        {"profit_factor": 2.0, "expectancy": 100, "max_drawdown_percent": 10},
        {"trades": 40, "profit_factor": 1.2, "expectancy": 80, "max_drawdown_percent": 12},
    )
    assert result["status"] == "NOT_READY"
    assert "PROFIT_FACTOR_DEGRADATION" in result["reasons"]


def test_divergence_gate_rejects_insufficient_paper_sample():
    result = evaluate_backtest_vs_paper(
        {"profit_factor": 1.8, "expectancy": 100, "max_drawdown_percent": 10},
        {"trades": 5, "profit_factor": 2.0, "expectancy": 120, "max_drawdown_percent": 5},
    )
    assert result["status"] == "NOT_READY"
    assert "INSUFFICIENT_PAPER_TRADES" in result["reasons"]


def test_divergence_gate_rejects_non_positive_paper_expectancy():
    result = evaluate_backtest_vs_paper(
        {"profit_factor": 1.5, "expectancy": 100, "max_drawdown_percent": 10},
        {"trades": 40, "profit_factor": 1.4, "expectancy": -1, "max_drawdown_percent": 12},
    )
    assert result["status"] == "NOT_READY"
    assert "NON_POSITIVE_PAPER_EXPECTANCY" in result["reasons"]
