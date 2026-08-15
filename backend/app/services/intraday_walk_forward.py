from __future__ import annotations

from typing import Sequence

from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest
from app.services.intraday_strategy import IntradayConfig
from app.services.intraday_strategy_comparison import compare_intraday_strategies
from app.services.walk_forward_service import build_walk_forward_windows


def _validation_summary(results: list[dict]) -> dict:
    if not results:
        return {"windows": 0, "profitable_windows": 0, "success_rate_percent": 0.0, "average_return_percent": 0.0, "worst_return_percent": 0.0, "max_drawdown_percent": 0.0}
    returns = [float(x["return_percent"]) for x in results]
    drawdowns = [float(x["max_drawdown_percent"]) for x in results]
    profitable = sum(value > 0 for value in returns)
    return {
        "windows": len(results),
        "profitable_windows": profitable,
        "success_rate_percent": round(profitable / len(results) * 100, 2),
        "average_return_percent": round(sum(returns) / len(returns), 4),
        "worst_return_percent": round(min(returns), 4),
        "max_drawdown_percent": round(max(drawdowns), 4),
    }


def run_fixed_parameter_walk_forward(
    rows: Sequence[dict],
    train_size: int = 60,
    validation_size: int = 20,
    step: int | None = None,
    config: IntradayBacktestConfig = IntradayBacktestConfig(),
) -> dict:
    """Run chronological out-of-sample windows with fixed parameters.

    The train slice is intentionally not used for parameter optimization. This keeps
    the first research implementation honest: every validation window is evaluated
    using parameters supplied before the run, preventing hidden look-ahead tuning.
    """
    windows = build_walk_forward_windows(len(rows), train_size, validation_size, step)
    v1_results: list[dict] = []
    v2_results: list[dict] = []
    comparisons: list[dict] = []
    for number, window in enumerate(windows, start=1):
        validation = rows[window.validation_start:window.validation_end]
        v1 = run_intraday_backtest(validation, config)
        v2_config = IntradayBacktestConfig(
            initial_capital=config.initial_capital,
            brokerage_rate=config.brokerage_rate,
            slippage_rate=config.slippage_rate,
            max_daily_loss_percent=config.max_daily_loss_percent,
            max_trades_per_session=config.max_trades_per_session,
            strategy=IntradayConfig(**config.strategy.__dict__),
            strategy_version="V2",
        )
        v2 = run_intraday_backtest(validation, v2_config)
        comparison = compare_intraday_strategies(validation, config)
        v1_results.append({"window": number, "train_start": window.train_start, "train_end": window.train_end, "validation_start": window.validation_start, "validation_end": window.validation_end, **{k: v for k, v in v1.items() if k != "trades_detail"}})
        v2_results.append({"window": number, "train_start": window.train_start, "train_end": window.train_end, "validation_start": window.validation_start, "validation_end": window.validation_end, **{k: v for k, v in v2.items() if k != "trades_detail"}})
        comparisons.append({"window": number, "validation_start": window.validation_start, "validation_end": window.validation_end, "delta": comparison["delta"]})
    return {
        "method": "fixed_parameter_walk_forward",
        "parameter_selection": False,
        "train_size": train_size,
        "validation_size": validation_size,
        "step": validation_size if step is None else step,
        "windows": len(windows),
        "v1": {"windows": v1_results, "summary": _validation_summary(v1_results)},
        "v2": {"windows": v2_results, "summary": _validation_summary(v2_results)},
        "comparison": comparisons,
    }
