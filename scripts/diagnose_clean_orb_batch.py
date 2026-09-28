from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose clean V1 ORB batch research results.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    rows = data["results"]
    if not rows:
        raise ValueError("Batch result contains no symbol results.")

    total_trades = sum(r["trades"] for r in rows)
    total_wins = sum(r["wins"] for r in rows)
    total_losses = sum(r["losses"] for r in rows)
    positive = [r for r in rows if r["net_pnl"] > 0]
    negative = [r for r in rows if r["net_pnl"] < 0]
    returns = sorted(r["return_percent"] for r in rows)
    pnls = sorted(r["net_pnl"] for r in rows)

    def median(values):
        n = len(values)
        return values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2

    report = {
        "status": "OK",
        "mode": data.get("mode", "SIMULATION_ONLY"),
        "symbol_count": len(rows),
        "positive_symbol_count": len(positive),
        "negative_symbol_count": len(negative),
        "zero_symbol_count": len(rows) - len(positive) - len(negative),
        "total_independent_trades": total_trades,
        "total_wins": total_wins,
        "total_losses": total_losses,
        "pooled_trade_win_rate": round(total_wins / total_trades * 100, 2) if total_trades else 0.0,
        "mean_symbol_return_percent": round(sum(returns) / len(returns), 4),
        "median_symbol_return_percent": round(median(returns), 4),
        "best_symbol_by_net_pnl": max(rows, key=lambda r: r["net_pnl"]),
        "worst_symbol_by_net_pnl": min(rows, key=lambda r: r["net_pnl"]),
        "largest_drawdown_symbol": max(rows, key=lambda r: r["max_drawdown_percent"]),
        "median_symbol_net_pnl": round(median(pnls), 2),
        "independent_net_pnl_sum": data.get("independent_net_pnl_sum"),
        "symbol_results": rows,
        "interpretation": [
            "This is descriptive historical simulation evidence only.",
            "The pooled trade win rate combines independent symbol simulations and is not a portfolio backtest.",
            "No parameter optimization or profitability claim is made by this report.",
            "Before changing parameters, inspect transaction-cost contribution, exit reasons, time/regime concentration, and data/corporate-action validity.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "symbol_count": report["symbol_count"],
        "positive_symbol_count": report["positive_symbol_count"],
        "negative_symbol_count": report["negative_symbol_count"],
        "pooled_trade_win_rate": report["pooled_trade_win_rate"],
        "mean_symbol_return_percent": report["mean_symbol_return_percent"],
        "median_symbol_return_percent": report["median_symbol_return_percent"],
        "best_symbol": report["best_symbol_by_net_pnl"]["symbol"],
        "worst_symbol": report["worst_symbol_by_net_pnl"]["symbol"],
        "largest_drawdown_symbol": report["largest_drawdown_symbol"]["symbol"],
        "output": str(args.output),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
