from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# The runner is stored under /scripts while the application package is under /backend.
# Add the backend root explicitly so the same command works from the repository backend directory.
BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

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
    strategy_version: str = "V1",
) -> dict[str, Any]:
    rows = load_symbol_dataset(root, symbol)
    by_session: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_session[row["session"]].append(row)

    session_results = []
    for session, session_rows in sorted(by_session.items()):
        result = run_intraday_backtest(
            session_rows,
            IntradayBacktestConfig(
                initial_capital=initial_capital,
                strategy_version=strategy_version,
            ),
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
        IntradayBacktestConfig(
            initial_capital=initial_capital,
            strategy_version=strategy_version,
        ),
    )
    return {
        "status": "OK",
        "mode": "SIMULATION_ONLY",
        "symbol": symbol.strip().upper(),
        "strategy_version": strategy_version,
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
            f"Strategy version under test: {strategy_version}.",
        ],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run descriptive clean Dhan equity research for a selected strategy version.")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--strategy-version", choices=["V1", "V2A"], default="V1")
    args = parser.parse_args()

    result = run_symbol_research(
        args.root,
        args.symbol,
        strategy_version=args.strategy_version,
    )
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
