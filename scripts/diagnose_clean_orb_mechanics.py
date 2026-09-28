from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import sys
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from run_clean_orb_research import load_symbol_dataset, run_symbol_research
from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest


def main() -> None:
    p = argparse.ArgumentParser(description="Diagnose V1 ORB entry/exit and cost mechanics per clean symbol.")
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--symbols", nargs="*", default=None)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()

    symbols = args.symbols or sorted(x.stem.upper() for x in (args.root / "dhan_equity_clean").glob("*.jsonl"))
    out: dict[str, Any] = {}
    for symbol in symbols:
        rows = load_symbol_dataset(args.root, symbol)
        result = run_intraday_backtest(rows, IntradayBacktestConfig())
        trades = result["trades_detail"]
        reasons = Counter(t["reason"] for t in trades)
        gross = float(result["gross_pnl"])
        costs = float(result["total_costs"])
        out[symbol] = {
            "sessions": len({r["session"] for r in rows}),
            "bars": len(rows),
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
            "max_drawdown_percent": result["max_drawdown_percent"],
            "exit_reason_counts": dict(sorted(reasons.items())),
            "average_hold_bars": None,
        }
        holds=[]
        timestamps={r["timestamp"]:i for i,r in enumerate(rows)}
        for t in trades:
            if t.get("entry_time") in timestamps and t.get("exit_time") in timestamps:
                holds.append(max(0, timestamps[t["exit_time"]]-timestamps[t["entry_time"]]))
        if holds:
            out[symbol]["average_hold_bars"]=round(sum(holds)/len(holds),2)

    summary={
        "status":"OK",
        "mode":"SIMULATION_ONLY",
        "symbols":out,
        "notes":[
            "Descriptive mechanics diagnostic; no parameter optimization.",
            "Gross P&L and explicit costs are separated so cost drag can be inspected.",
            "Exit reason counts are based on the current backtest fill model.",
        ],
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"symbols":len(out),"output":str(args.output)},indent=2))


if __name__=="__main__":
    main()
