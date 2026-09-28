from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from run_clean_orb_research import run_symbol_research


def main() -> None:
    parser = argparse.ArgumentParser(description="Run descriptive V1 ORB research across clean Dhan equity symbols.")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--symbols",
        nargs="*",
        default=None,
        help="Optional symbols. If omitted, all symbol-partitioned clean JSONL files are used.",
    )
    args = parser.parse_args()

    data_dir = args.root / "dhan_equity_clean"
    if not data_dir.exists():
        raise FileNotFoundError(f"Clean research directory not found: {data_dir}")

    symbols = (
        [s.strip().upper() for s in args.symbols if s.strip()]
        if args.symbols
        else sorted(p.stem.upper() for p in data_dir.glob("*.jsonl"))
    )
    if not symbols:
        raise FileNotFoundError(f"No symbol-partitioned JSONL files found under {data_dir}")

    results: dict[str, Any] = {}
    failures: dict[str, str] = {}
    for symbol in symbols:
        try:
            results[symbol] = run_symbol_research(args.root, symbol)
        except Exception as exc:
            failures[symbol] = f"{type(exc).__name__}: {exc}"

    summary = []
    for symbol, result in results.items():
        aggregate = result["aggregate"]
        summary.append({
            "symbol": symbol,
            "sessions": result["sessions"],
            "bars": result["bars"],
            "trades": aggregate["trades"],
            "wins": aggregate["wins"],
            "losses": aggregate["losses"],
            "ending_capital": aggregate["ending_capital"],
            "net_pnl": aggregate["ending_capital"] - aggregate["initial_capital"],
            "return_percent": aggregate["return_percent"],
            "max_drawdown_percent": aggregate["max_drawdown_percent"],
            "strategy_fingerprint": aggregate["strategy_fingerprint"],
        })

    payload = {
        "status": "OK" if not failures else "PARTIAL",
        "mode": "SIMULATION_ONLY",
        "symbols_requested": symbols,
        "symbols_completed": sorted(results),
        "symbols_failed": failures,
        "summary": summary,
        "results": results,
        "warnings": [
            "Historical simulation evidence only; this is not a live or paper-trading result.",
            "The source universe is survivorship-biased until historical membership is available.",
            "Corporate-action adjustment status must be established before long-horizon conclusions.",
            "No parameter optimization is performed by this runner.",
            "Per-symbol session results use independent initial capital; they must not be summed as a compounded portfolio result.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": payload["status"],
        "symbols_completed": len(results),
        "symbols_failed": len(failures),
        "output": str(args.output),
        "summary": summary,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
