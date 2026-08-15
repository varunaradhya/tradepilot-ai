from dataclasses import replace

from app.services.intraday_backtest import IntradayBacktestConfig
from app.services.intraday_robustness import build_robustness_variants, run_robustness_analysis
from app.services.intraday_strategy import IntradayConfig


def test_robustness_variants_are_fixed_and_do_not_duplicate_base():
    strategy = IntradayConfig()
    variants = build_robustness_variants(strategy)
    names = [name for name, _ in variants]
    assert names[0] == "BASE"
    assert len(names) == len(set(names))
    assert all(candidate.fast_period < candidate.slow_period for _, candidate in variants)
    assert all(candidate.fast_period == strategy.fast_period for name, candidate in variants if name not in {"FAST_MINUS_1", "FAST_PLUS_1"})


def test_robustness_handles_empty_data_without_optimization():
    config = IntradayBacktestConfig(strategy=IntradayConfig())
    result = run_robustness_analysis([], config)
    assert result["summary"]["variant_count"] == 0
    assert result["variants"] == []


def test_robustness_reports_cost_stress_as_a_diagnostic():
    rows = []
    strategy = IntradayConfig()
    config = IntradayBacktestConfig(strategy=strategy)
    result = run_robustness_analysis(rows, config, stress_costs=True)
    assert result["method"].startswith("fixed local sensitivity")
    assert result["summary"]["variant_count"] == 0
