from __future__ import annotations

from typing import Any, Sequence

from app.services.fno_backtest_service import FNOBacktestConfig, run_fno_backtest


def run_fno_execution_stress(
    *,
    underlying: dict[str, Any],
    bars: Sequence[dict[str, Any]],
    option_chain_snapshots: Sequence[dict[str, Any]],
    lot_size: int,
    initial_capital: float = 100_000.0,
    risk_per_trade: float = 0.005,
    max_capital_percent: float = 0.50,
    slippage_rates: Sequence[float] = (0.0, 0.001, 0.002),
    spread_limits: Sequence[float | None] = (None, 1.5, 3.0),
) -> dict[str, Any]:
    """Run frozen strategy replay under execution-friction scenarios.

    This function never tunes strategy parameters. It only reruns the same
    decision stream with progressively harsher execution assumptions.
    """
    scenarios: list[dict[str, Any]] = []
    for slippage in slippage_rates:
        for spread in spread_limits:
            if slippage < 0:
                raise ValueError("slippage rates must be non-negative")
            result = run_fno_backtest(
                underlying=underlying,
                bars=bars,
                option_chain_snapshots=option_chain_snapshots,
                lot_size=lot_size,
                config=FNOBacktestConfig(
                    initial_capital=initial_capital,
                    risk_per_trade=risk_per_trade,
                    max_capital_percent=max_capital_percent,
                    slippage_rate=float(slippage),
                    max_spread_percent=spread,
                ),
            )
            scenarios.append({
                "slippage_rate": float(slippage),
                "max_spread_percent": spread,
                "return_percent": result["return_percent"],
                "profit_factor": result["profit_factor"],
                "expectancy_per_trade": result["expectancy_per_trade"],
                "max_drawdown_percent": result["max_drawdown_percent"],
                "trades": result["trades"],
            })

    return {"scenario_count": len(scenarios), "scenarios": scenarios}
