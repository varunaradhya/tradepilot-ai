from __future__ import annotations

import json
from pathlib import Path

from compare_clean_orb_v1_v2a import metrics


def test_metrics_extracts_core_backtest_fields() -> None:
    result = {
        "trades": 4, "wins": 1, "losses": 3,
        "win_rate_percent": 25.0, "profit_factor": 0.8,
        "expectancy": -10.0, "gross_pnl": 20.0,
        "total_costs": 60.0, "cost_drag_percent": 0.06,
        "ending_capital": 99960.0, "initial_capital": 100000.0,
        "return_percent": -0.04, "max_drawdown_percent": 0.1,
    }
    assert metrics(result)["net_pnl"] == -40.0
    assert metrics(result)["trades"] == 4


def test_comparison_schema_is_json_serializable(tmp_path: Path) -> None:
    report = {
        "status": "OK",
        "mode": "SIMULATION_ONLY",
        "comparison": "V1_vs_V2A",
        "aggregate": {},
        "symbols": [],
    }
    path = tmp_path / "comparison.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    assert json.loads(path.read_text(encoding="utf-8"))["comparison"] == "V1_vs_V2A"
