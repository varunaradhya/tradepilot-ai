from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest


def main() -> None:
    p = argparse.ArgumentParser(description="Compare V1 ORB gross signal behavior under execution-friction scenarios.")
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--symbols", nargs="*", default=None)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()

    clean = args.root / "dhan_equity_clean"
    symbols = args.symbols or sorted(x.stem.upper() for x in clean.glob("*.jsonl"))
    scenarios = {
        "frictionless": {"brokerage_rate": 0.0, "slippage_rate": 0.0},
        "brokerage_only": {"brokerage_rate": 0.0003, "slippage_rate": 0.0},
        "slippage_only": {"brokerage_rate": 0.0, "slippage_rate": 0.0005},
        "baseline": {"brokerage_rate": 0.0003, "slippage_rate": 0.0005},
    }
    results = {}
    for symbol in symbols:
        rows = [json.loads(x) for x in (clean / f"{symbol}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        for r in rows:
            from datetime import datetime
            r["session"] = datetime.fromisoformat(r["timestamp"]).date().isoformat()
        results[symbol] = {}
        for name, friction in scenarios.items():
            result = run_intraday_backtest(rows, IntradayBacktestConfig(**friction))
            results[symbol][name] = {
                "trades": result["trades"],
                "win_rate_percent": result["win_rate_percent"],
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
        "scenarios": scenarios,
        "results": results,
        "notes": [
            "This is a descriptive friction-sensitivity diagnostic, not parameter optimization.",
            "Frictionless results are a signal-behavior diagnostic and are not executable performance evidence.",
            "Baseline uses the existing backtest execution assumptions.",
        ],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"symbols": len(results), "scenarios": list(scenarios), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
