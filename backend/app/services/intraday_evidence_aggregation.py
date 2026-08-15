from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from app.models.paper_trade import PaperTrade


def aggregate_scorecards(scorecards: Iterable[dict], *, interval: str, requested_symbols: list[str], missing_symbols: list[str]) -> dict:
    items = [item for item in scorecards if item.get("status") != "NO_DATA"]
    robust = [item for item in items if item.get("robustness", {}).get("status") == "ROBUST"]
    returns = [float(item.get("metrics", {}).get("return_percent") or 0.0) for item in items]
    profit_factors = [float(item.get("metrics", {}).get("profit_factor") or 0.0) for item in items]
    drawdowns = [float(item.get("metrics", {}).get("max_drawdown_percent") or 0.0) for item in items]
    return {
        "status": "OK" if items else "NO_DATA",
        "interval": interval,
        "requested_symbols": requested_symbols,
        "available_symbols": [str(item.get("symbol", "")).upper() for item in items],
        "missing_symbols": missing_symbols,
        "summary": {
            "symbols_tested": len(items),
            "robust_symbols": len(robust),
            "robust_percent": round(len(robust) / len(items) * 100, 2) if items else 0.0,
            "average_return_percent": round(sum(returns) / len(returns), 2) if returns else 0.0,
            "median_profit_factor": round(sorted(profit_factors)[len(profit_factors) // 2], 2) if profit_factors else 0.0,
            "worst_drawdown_percent": round(max(drawdowns), 2) if drawdowns else 0.0,
        },
        "ranking": sorted(items, key=lambda item: float(item.get("score", float("-inf"))), reverse=True),
        "research_policy": {
            "parameter_selection": False,
            "cross_stock_optimization": False,
            "qualification_requires_separate_walk_forward": True,
        },
    }


def aggregate_paper_performance(trades: Iterable[PaperTrade]) -> dict:
    rows = list(trades)
    closed = [trade for trade in rows if trade.status == "CLOSED"]
    by_symbol: dict[str, dict] = defaultdict(lambda: {"trades": 0, "closed_trades": 0, "pnl": 0.0, "wins": 0})
    by_reason: dict[str, int] = defaultdict(int)
    for trade in rows:
        symbol = str(trade.symbol).upper()
        item = by_symbol[symbol]
        item["trades"] += 1
        if trade.status == "CLOSED":
            item["closed_trades"] += 1
            item["pnl"] += float(trade.pnl or 0.0)
            if float(trade.pnl or 0.0) > 0:
                item["wins"] += 1
            by_reason[str(trade.reason or "UNKNOWN").upper()] += 1
    for item in by_symbol.values():
        item["pnl"] = round(item["pnl"], 2)
        item["win_rate_percent"] = round(item["wins"] / item["closed_trades"] * 100, 2) if item["closed_trades"] else 0.0
    realized = sum(float(trade.pnl or 0.0) for trade in closed)
    wins = sum(1 for trade in closed if float(trade.pnl or 0.0) > 0)
    return {
        "mode": "SIMULATION_ONLY",
        "summary": {
            "trades": len(rows),
            "open_trades": len(rows) - len(closed),
            "closed_trades": len(closed),
            "realized_pnl": round(realized, 2),
            "win_rate_percent": round(wins / len(closed) * 100, 2) if closed else 0.0,
        },
        "by_symbol": dict(sorted(by_symbol.items())),
        "exit_reasons": dict(sorted(by_reason.items())),
    }
