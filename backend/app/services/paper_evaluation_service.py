from __future__ import annotations

from typing import Any


def evaluate_replay(result: dict[str, Any]) -> dict[str, Any]:
    metrics = dict(result.get("metrics") or {})
    trades = list(result.get("trades") or [])
    return {
        "mode": "SIMULATION_ONLY",
        "summary": metrics,
        "evidence": {
            "sample_size": len(trades),
            "has_minimum_sample": len(trades) >= 30,
            "metrics_available": bool(trades),
            "note": "Metrics are descriptive replay results, not a profitability guarantee or a qualification verdict.",
        },
    }


def compare_strategy_results(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    # No ranking/winner is emitted. This is intentionally a side-by-side evidence matrix.
    return {
        "mode": "SIMULATION_ONLY",
        "strategies": {
            name: {
                "metrics": dict(value.get("metrics") or {}),
                "sample_size": len(value.get("trades") or []),
            }
            for name, value in results.items()
        },
        "note": "Comparison is descriptive; TradePilot does not automatically select a winning strategy.",
    }
