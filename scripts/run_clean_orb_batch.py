from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Scripts live above /backend; expose the application package and sibling runner.
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from run_clean_orb_research import run_symbol_research


def discover_symbols(root: Path) -> list[str]:
    directory = root / "dhan_equity_clean"
    if not directory.exists():
        raise FileNotFoundError(f"Clean research directory not found: {directory}")
    return sorted(p.stem.upper() for p in directory.glob("*.jsonl") if p.is_file())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run descriptive V1 ORB research across clean Dhan equity symbols."
    )
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--symbols", nargs="*", help="Optional symbol list; default is every clean symbol file.")
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols] if args.symbols else discover_symbols(args.root)
    if not symbols:
        raise ValueError("No clean symbol datasets found.")

    results: dict[str, Any] = {}
    for symbol in symbols:
        results[symbol] = run_symbol_research(args.root, symbol)

    rows = []
    for symbol, result in results.items():
        aggregate = result["aggregate"]
        rows.append({
            "symbol": symbol,
            "sessions": result["sessions"],
            "bars": result["bars"],
            "trades": aggregate["trades"],
            "wins": aggregate["wins"],
            "losses": aggregate["losses"],
            "net_pnl": round(aggregate["ending_capital"] - aggregate["initial_capital"], 2),
            "return_percent": aggregate["return_percent"],
            "max_drawdown_percent": aggregate["max_drawdown_percent"],
            "strategy_fingerprint": aggregate["strategy_fingerprint"],
        })

    independent_net_pnl_sum = round(sum(row["net_pnl"] for row in rows), 2)
    output = {
        "status": "OK",
        "mode": "SIMULATION_ONLY",
        "symbols": [row["symbol"] for row in rows],
        "symbol_count": len(rows),
        "results": rows,
        "portfolio_note": (
            "Each symbol is an independent 100000-capital simulation. "
            "independent_net_pnl_sum is a descriptive sum only, not a portfolio backtest "
            "and not evidence of deployable profitability."
        ),
        "independent_net_pnl_sum": independent_net_pnl_sum,
        "warnings": [
            "Historical simulation evidence only; no live execution.",
            "The source universe is survivorship-biased until historical membership is available.",
            "Corporate-action adjustment status must be established before long-horizon conclusions.",
            "No parameter optimization is performed by this batch runner.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "symbol_count": len(rows),
        "symbols": [row["symbol"] for row in rows],
        "independent_net_pnl_sum": independent_net_pnl_sum,
        "output": str(args.output),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
