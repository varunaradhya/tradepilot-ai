from __future__ import annotations

from dataclasses import replace
from statistics import median
from typing import Sequence

from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest
from app.services.intraday_strategy import IntradayConfig


def _variant(name: str, strategy: IntradayConfig, **changes) -> tuple[str, IntradayConfig]:
    return name, replace(strategy, **changes)


def build_robustness_variants(strategy: IntradayConfig) -> list[tuple[str, IntradayConfig]]:
    """Build a fixed sensitivity set around the chosen parameters; never select a winner."""
    variants: list[tuple[str, IntradayConfig]] = [("BASE", strategy)]
    variants.extend([
        _variant("FAST_MINUS_1", strategy, fast_period=max(2, strategy.fast_period - 1)),
        _variant("FAST_PLUS_1", strategy, fast_period=min(strategy.slow_period - 1, strategy.fast_period + 1)),
        _variant("SLOW_MINUS_2", strategy, slow_period=max(strategy.fast_period + 1, strategy.slow_period - 2)),
        _variant("SLOW_PLUS_2", strategy, slow_period=strategy.slow_period + 2),
        _variant("VOLUME_MINUS_0_2", strategy, min_volume_ratio=max(0.1, strategy.min_volume_ratio - 0.2)),
        _variant("VOLUME_PLUS_0_2", strategy, min_volume_ratio=strategy.min_volume_ratio + 0.2),
        _variant("ATR_MINUS_0_2", strategy, atr_stop_multiple=max(0.1, strategy.atr_stop_multiple - 0.2)),
        _variant("ATR_PLUS_0_2", strategy, atr_stop_multiple=strategy.atr_stop_multiple + 0.2),
        _variant("REWARD_MINUS_0_25", strategy, reward_multiple=max(0.1, strategy.reward_multiple - 0.25)),
        _variant("REWARD_PLUS_0_25", strategy, reward_multiple=strategy.reward_multiple + 0.25),
    ])
    return variants


def run_robustness_analysis(
    rows: Sequence[dict],
    config: IntradayBacktestConfig,
    *,
    stress_costs: bool = True,
) -> dict:
    """Measure sensitivity to small parameter changes and execution-cost stress.

    This is diagnostic only: no variant is selected or fed back into the strategy.
    """
    if not rows:
        return {"variants": [], "summary": {"variant_count": 0, "positive_return_percent": 0.0, "median_return_percent": 0.0}}

    base = config.strategy if isinstance(config.strategy, IntradayConfig) else IntradayConfig()
    results: list[dict] = []
    for name, strategy in build_robustness_variants(base):
        result = run_intraday_backtest(rows, replace(config, strategy=strategy, strategy_version="V1"))
        results.append({
            "name": name,
            "return_percent": result["return_percent"],
            "profit_factor": result["profit_factor"],
            "win_rate_percent": result["win_rate_percent"],
            "expectancy": result["expectancy"],
            "max_drawdown_percent": result["max_drawdown_percent"],
            "trades": result["trades"],
        })

    if stress_costs:
        stressed = replace(config, slippage_rate=config.slippage_rate * 2, brokerage_rate=config.brokerage_rate * 1.25)
        result = run_intraday_backtest(rows, replace(stressed, strategy=base, strategy_version="V1"))
        results.append({
            "name": "COST_STRESS_2X_SLIPPAGE_1_25X_BROKERAGE",
            "return_percent": result["return_percent"],
            "profit_factor": result["profit_factor"],
            "win_rate_percent": result["win_rate_percent"],
            "expectancy": result["expectancy"],
            "max_drawdown_percent": result["max_drawdown_percent"],
            "trades": result["trades"],
        })

    returns = [float(item["return_percent"]) for item in results]
    positive = sum(1 for value in returns if value > 0)
    base_result = next(item for item in results if item["name"] == "BASE")
    stable_pf = sum(1 for item in results if item["profit_factor"] is not None and item["profit_factor"] > 1)
    return {
        "method": "fixed local sensitivity; no parameter optimization",
        "variants": results,
        "summary": {
            "variant_count": len(results),
            "positive_return_percent": round(positive / len(results) * 100, 2),
            "profit_factor_above_1_percent": round(stable_pf / len(results) * 100, 2),
            "median_return_percent": round(median(returns), 2),
            "worst_return_percent": min(returns),
            "best_return_percent": max(returns),
            "base_return_percent": base_result["return_percent"],
            "base_max_drawdown_percent": base_result["max_drawdown_percent"],
        },
    }
