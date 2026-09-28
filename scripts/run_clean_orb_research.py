from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest


def load_symbol_dataset(root: Path, symbol: str) -> list[dict[str, Any]]:
    path = root / "dhan_equity_clean" / f"{symbol.strip().upper()}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Clean research dataset not found: {path}")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        row["session"] = datetime.fromisoformat(row["timestamp"]).date().isoformat()
    return rows


def run_symbol_research(
    root: Path,
    symbol: str,
    *,
    initial_capital: float = 100000.0,
) -> dict[str, Any]:
    rows = load_symbol_dataset(root, symbol)
    by_session: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_session[row["session"]].append(row)

    session_results = []
    for session, session_rows in sorted(by_session.items()):
        result = run_intraday_backtest(
            session_rows,
            IntradayBacktestConfig(initial_capital=initial_capital),
        )
        session_results.append({
            "session": session,
            "bars": len(session_rows),
            "trades": result["trades"],
            "wins": result["wins"],
            "losses": result["losses"],
            "net_pnl": result["ending_capital"] - initial_capital,
            "return_percent": result["return_percent"],
            "max_drawdown_percent": result["max_drawdown_percent"],
            "strategy_fingerprint": result["strategy_fingerprint"],
        })

    aggregate = run_intraday_backtest(
        rows,
        IntradayBacktestConfig(initial_capital=initial_capital),
    )
    return {
        "status": "OK",
        "mode": "SIMULATION_ONLY",
        "symbol": symbol.strip().upper(),
        "dataset": f"dhan_equity_clean/{symbol.strip().upper()}.jsonl",
        "sessions": len(session_results),
        "bars": len(rows),
        "session_results": session_results,
        "aggregate": {k: v for k, v in aggregate.items() if k != "trades_detail"},
        "warnings": [
            "This is historical simulation evidence, not a live or paper-trading result.",
            "The source universe is survivorship-biased until historical membership is available.",
            "Corporate-action adjustment status of the source data must be established before long-horizon conclusions.",
            "No parameter optimization is performed by this runner.",
        ],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run descriptive V1 ORB research on one clean Dhan equity symbol.")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    result = run_symbol_research(args.root, args.symbol)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "symbol": result["symbol"],
        "sessions": result["sessions"],
        "bars": result["bars"],
        "trades": result["aggregate"]["trades"],
        "net_pnl": result["aggregate"]["ending_capital"] - result["aggregate"]["initial_capital"],
        "return_percent": result["aggregate"]["return_percent"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
