from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from run_clean_orb_research import load_symbol_dataset
from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest
from app.services.intraday_strategy import IntradayConfig
from app.services.intraday_strategy_v2 import IntradayV2AConfig


def run_symbol(root: Path, symbol: str, version: str) -> dict[str, Any]:
    rows = load_symbol_dataset(root, symbol)
    strategy = IntradayConfig()
    if version == "V2A":
        strategy = IntradayV2AConfig(**strategy.__dict__)
    result = run_intraday_backtest(
        rows,
        IntradayBacktestConfig(strategy=strategy, strategy_version=version),
    )
    return result


def metrics(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "trades": result["trades"],
        "wins": result["wins"],
        "losses": result["losses"],
        "win_rate_percent": result["win_rate_percent"],
        "profit_factor": result["profit_factor"],
        "expectancy": result["expectancy"],
        "gross_pnl": result["gross_pnl"],
        "total_costs": result["total_costs"],
        "cost_drag_percent": result["cost_drag_percent"],
        "net_pnl": round(result["ending_capital"] - result["initial_capital"], 2),
        "return_percent": result["return_percent"],
        "max_drawdown_percent": result["max_drawdown_percent"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descriptive V1 vs V2A comparison on the frozen clean Dhan research universe."
    )
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--symbols", nargs="*", default=None)
    args = parser.parse_args()

    clean_dir = args.root / "dhan_equity_clean"
    symbols = (
        [s.strip().upper() for s in args.symbols]
        if args.symbols
        else sorted(p.stem.upper() for p in clean_dir.glob("*.jsonl"))
    )
    if not symbols:
        raise ValueError("No clean symbol datasets found.")

    rows = []
    for symbol in symbols:
        v1 = run_symbol(args.root, symbol, "V1")
        v2a = run_symbol(args.root, symbol, "V2A")
        m1 = metrics(v1)
        m2 = metrics(v2a)
        rows.append({
            "symbol": symbol,
            "V1": m1,
            "V2A": m2,
            "delta_V2A_minus_V1": {
                key: round(m2[key] - m1[key], 4)
                for key in (
                    "trades", "wins", "losses", "win_rate_percent", "expectancy",
                    "gross_pnl", "total_costs", "net_pnl", "return_percent",
                    "max_drawdown_percent",
                )
            },
        })

    def sum_metric(version: str, key: str) -> float:
        return sum(float(r[version][key]) for r in rows)

    v1_trades = sum_metric("V1", "trades")
    v2a_trades = sum_metric("V2A", "trades")
    v1_wins = sum_metric("V1", "wins")
    v2a_wins = sum_metric("V2A", "wins")
    v1_net = sum_metric("V1", "net_pnl")
    v2a_net = sum_metric("V2A", "net_pnl")

    aggregate = {
        "V1": {
            "independent_net_pnl_sum": round(v1_net, 2),
            "independent_gross_pnl_sum": round(sum_metric("V1", "gross_pnl"), 2),
            "independent_cost_sum": round(sum_metric("V1", "total_costs"), 2),
            "independent_trade_count": int(v1_trades),
            "pooled_win_rate_percent": round(v1_wins / v1_trades * 100, 2) if v1_trades else 0.0,
        },
        "V2A": {
            "independent_net_pnl_sum": round(v2a_net, 2),
            "independent_gross_pnl_sum": round(sum_metric("V2A", "gross_pnl"), 2),
            "independent_cost_sum": round(sum_metric("V2A", "total_costs"), 2),
            "independent_trade_count": int(v2a_trades),
            "pooled_win_rate_percent": round(v2a_wins / v2a_trades * 100, 2) if v2a_trades else 0.0,
        },
        "delta_V2A_minus_V1": {
            "net_pnl": round(v2a_net - v1_net, 2),
            "gross_pnl": round(sum_metric("V2A", "gross_pnl") - sum_metric("V1", "gross_pnl"), 2),
            "costs": round(sum_metric("V2A", "total_costs") - sum_metric("V1", "total_costs"), 2),
            "trades": int(v2a_trades - v1_trades),
            "pooled_win_rate_percentage_points": round(
                (v2a_wins / v2a_trades * 100 if v2a_trades else 0.0)
                - (v1_wins / v1_trades * 100 if v1_trades else 0.0), 2
            ),
        },
    }

    report = {
        "status": "OK",
        "mode": "SIMULATION_ONLY",
        "comparison": "V1_vs_V2A",
        "symbol_count": len(rows),
        "aggregate": aggregate,
        "symbols": rows,
        "interpretation": [
            "This is descriptive historical simulation evidence only.",
            "The independent sums are not a portfolio backtest.",
            "V1 and V2A use the same clean datasets and execution assumptions; V2A adds breakout-quality filters.",
            "No parameter optimization is performed by this comparison.",
            "A positive delta means V2A was less negative or more positive than V1; it does not establish profitability.",
            "Inspect trade-count reduction, gross P&L, cost reduction, and per-symbol consistency before adding another strategy layer.",
            "The research universe remains survivorship-biased until historical membership is available, and corporate-action adjustment status remains a prerequisite for strong long-horizon conclusions.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "symbol_count": len(rows),
        "V1_independent_net_pnl_sum": aggregate["V1"]["independent_net_pnl_sum"],
        "V2A_independent_net_pnl_sum": aggregate["V2A"]["independent_net_pnl_sum"],
        "V2A_minus_V1_net_pnl": aggregate["delta_V2A_minus_V1"]["net_pnl"],
        "V1_trade_count": aggregate["V1"]["independent_trade_count"],
        "V2A_trade_count": aggregate["V2A"]["independent_trade_count"],
        "trade_reduction_percent": round(
            (1 - aggregate["V2A"]["independent_trade_count"] / aggregate["V1"]["independent_trade_count"]) * 100,
            2,
        ) if aggregate["V1"]["independent_trade_count"] else 0.0,
        "V1_gross_pnl_sum": aggregate["V1"]["independent_gross_pnl_sum"],
        "V2A_gross_pnl_sum": aggregate["V2A"]["independent_gross_pnl_sum"],
        "V1_cost_sum": aggregate["V1"]["independent_cost_sum"],
        "V2A_cost_sum": aggregate["V2A"]["independent_cost_sum"],
        "gross_pnl_delta": aggregate["delta_V2A_minus_V1"]["gross_pnl"],
        "cost_delta": aggregate["delta_V2A_minus_V1"]["costs"],
        "win_rate_delta_percentage_points": aggregate["delta_V2A_minus_V1"]["pooled_win_rate_percentage_points"],
        "output": str(args.output),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
