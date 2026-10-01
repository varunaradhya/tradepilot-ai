from __future__ import annotations

from dataclasses import asdict
from itertools import product
from typing import Sequence

from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest
from app.services.intraday_strategy import IntradayConfig


def _split(rows: Sequence[dict], train_fraction: float) -> tuple[list[dict], list[dict]]:
    cut = max(1, min(len(rows) - 1, int(len(rows) * train_fraction)))
    return list(rows[:cut]), list(rows[cut:])


def _candidate_configs(base: IntradayConfig) -> list[IntradayConfig]:
    # Deliberately small, interpretable grid. This is discovery, not an
    # unconstrained optimizer, and candidates are evaluated on a held-out
    # chronological segment.
    grid = product(
        (2, 3, 4),
        (9, 12),
        (1.25, 1.5),
        (2.0, 2.5),
    )
    candidates: list[IntradayConfig] = []
    seen: set[tuple] = set()
    for opening_bars, fast_period, atr_stop, reward in grid:
        slow_period = 20
        key = (opening_bars, fast_period, slow_period, atr_stop, reward)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            IntradayConfig(
                trade_direction=base.trade_direction,
                opening_bars=opening_bars,
                fast_period=fast_period,
                slow_period=slow_period,
                volume_period=base.volume_period,
                min_volume_ratio=base.min_volume_ratio,
                max_gap_percent=base.max_gap_percent,
                risk_per_trade=base.risk_per_trade,
                max_position_percent=base.max_position_percent,
                atr_period=base.atr_period,
                atr_stop_multiple=atr_stop,
                reward_multiple=reward,
                min_quality_score=base.min_quality_score,
                require_trending_regime=base.require_trending_regime,
            )
        )
    return candidates


def _run(rows: Sequence[dict], strategy: IntradayConfig, capital: float) -> dict:
    return run_intraday_backtest(
        rows,
        IntradayBacktestConfig(
            initial_capital=capital,
            strategy=strategy,
            strategy_version="V1",
        ),
    )


def _candidate_result(strategy: IntradayConfig, train_rows: list[dict], test_rows: list[dict], capital: float, min_test_trades: int) -> dict:
    train = _run(train_rows, strategy, capital)
    test = _run(test_rows, strategy, capital)
    test_trades = int(test["trades"])
    pf = test["profit_factor"]
    # Score rewards positive held-out expectancy/return and penalizes drawdown.
    # It is only a screening score; it is not a promise of future performance.
    score = (
        float(test["return_percent"])
        + (float(pf) * 5.0 if pf is not None else -10.0)
        + float(test["expectancy"]) / max(capital, 1.0) * 10000.0
        - float(test["max_drawdown_percent"]) * 0.5
    )
    return {
        "parameters": asdict(strategy),
        "train": {k: train[k] for k in ("return_percent", "trades", "win_rate_percent", "profit_factor", "expectancy", "max_drawdown_percent")},
        "test": {k: test[k] for k in ("return_percent", "trades", "win_rate_percent", "profit_factor", "expectancy", "max_drawdown_percent")},
        "screening_score": round(score, 4),
        "sufficient_test_trades": test_trades >= min_test_trades,
    }


def discover_intraday_strategies(
    datasets: dict[str, Sequence[dict]],
    *,
    base: IntradayConfig = IntradayConfig(),
    initial_capital: float = 100000.0,
    train_fraction: float = 0.70,
    min_test_trades: int = 10,
) -> dict:
    if not datasets:
        return {"status": "NO_DATA", "candidates": [], "symbols_tested": 0}
    if not 0.5 <= train_fraction < 1:
        raise ValueError("train_fraction must be between 0.5 and 1.0")
    candidates = _candidate_configs(base)
    aggregate: list[dict] = []

    for index, strategy in enumerate(candidates, start=1):
        symbol_results = []
        for symbol, rows in datasets.items():
            if len(rows) < 100:
                continue
            train_rows, test_rows = _split(rows, train_fraction)
            result = _candidate_result(strategy, train_rows, test_rows, initial_capital, min_test_trades)
            result["symbol"] = symbol
            symbol_results.append(result)

        eligible = [r for r in symbol_results if r["test"]["trades"] >= min_test_trades]
        if not symbol_results:
            continue

        test_returns = [float(r["test"]["return_percent"]) for r in symbol_results]
        test_pfs = [float(r["test"]["profit_factor"]) for r in eligible if r["test"]["profit_factor"] is not None]
        test_dd = [float(r["test"]["max_drawdown_percent"]) for r in symbol_results]
        robust_fraction = (
            sum(
                1 for r in eligible
                if float(r["test"]["return_percent"]) > 0 and (r["test"]["profit_factor"] or 0) >= 1
            ) / len(eligible)
            if eligible else 0.0
        )
        aggregate.append({
            "candidate_id": f"ORB-{index:02d}",
            "parameters": asdict(strategy),
            "symbols_tested": len(symbol_results),
            "symbols_with_minimum_test_trades": len(eligible),
            "robust_fraction_percent": round(robust_fraction * 100, 2),
            "average_test_return_percent": round(sum(test_returns) / len(test_returns), 2),
            "median_test_profit_factor": round(sorted(test_pfs)[len(test_pfs) // 2], 2) if test_pfs else None,
            "worst_test_drawdown_percent": round(max(test_dd), 2) if test_dd else 0.0,
            "average_screening_score": round(sum(float(r["screening_score"]) for r in symbol_results) / len(symbol_results), 4),
            "per_symbol": symbol_results,
        })

    aggregate.sort(
        key=lambda r: (
            r["robust_fraction_percent"],
            r["symbols_with_minimum_test_trades"],
            r["average_screening_score"],
        ),
        reverse=True,
    )
    return {
        "status": "OK" if aggregate else "NO_DATA",
        "method": "chronological_holdout_grid_discovery",
        "research_only": True,
        "parameter_selection": True,
        "train_fraction": train_fraction,
        "min_test_trades": min_test_trades,
        "symbols_requested": list(datasets),
        "symbols_tested": len(datasets),
        "candidate_count": len(aggregate),
        "candidates": aggregate,
        "warning": "Historical discovery is not proof of future performance. Candidates must be revalidated out-of-sample and in paper trading before any live deployment.",
    }
