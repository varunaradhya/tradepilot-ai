from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest
from app.services.intraday_strategy import IntradayConfig


def load_rows(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        row["session"] = datetime.fromisoformat(row["timestamp"]).date().isoformat()
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description="Run descriptive V1 ORB position-sizing sensitivity.")
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--symbols", nargs="*", default=None)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()

    clean = args.root / "dhan_equity_clean"
    symbols = args.symbols or sorted(x.stem.upper() for x in clean.glob("*.jsonl"))
    allocations = (0.02, 0.05, 0.10, 0.20)

    results = {}
    for symbol in symbols:
        rows = load_rows(clean / f"{symbol}.jsonl")
        results[symbol] = {}
        for allocation in allocations:
            strategy = replace(IntradayConfig(), max_position_percent=allocation)
            result = run_intraday_backtest(
                rows,
                IntradayBacktestConfig(strategy=strategy),
            )
            results[symbol][f"{allocation:.0%}"] = {
                "initial_capital": result["initial_capital"],
                "ending_capital": result["ending_capital"],
                "trades": result["trades"],
                "wins": result["wins"],
                "losses": result["losses"],
                "win_rate_percent": result["win_rate_percent"],
                "profit_factor": result["profit_factor"],
                "expectancy": result["expectancy"],
                "gross_pnl": result["gross_pnl"],
                "total_costs": result["total_costs"],
                "net_pnl": round(result["ending_capital"] - result["initial_capital"], 2),
                "return_percent": result["return_percent"],
                "max_drawdown_percent": result["max_drawdown_percent"],
            }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "status": "OK",
        "mode": "SIMULATION_ONLY",
        "allocations": list(f"{x:.0%}" for x in allocations),
        "results": results,
        "notes": [
            "Descriptive position-sizing sensitivity only; no parameter optimization.",
            "Signals, stops, targets, costs, and data are unchanged across scenarios.",
            "This does not represent a portfolio backtest or deployable performance.",
        ],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"symbols": len(results), "allocations": [f"{x:.0%}" for x in allocations], "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
