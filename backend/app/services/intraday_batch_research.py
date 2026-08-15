from __future__ import annotations

from typing import Sequence

from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest
from app.services.research_store import ResearchStore, research_store


def _year(row: dict) -> int:
    value = row.get("timestamp") or row.get("datetime") or row.get("date")
    if hasattr(value, "year"):
        return int(value.year)
    return int(str(value)[:4])


def _rows(store: ResearchStore, symbol: str, interval: str) -> list[dict]:
    dataset = f"nse/{symbol.strip().upper()}_intraday_{interval}m"
    bars = store.load(dataset)
    rows = []
    for bar in bars:
        row = bar.as_row()
        row["session"] = row["timestamp"].date().isoformat()
        rows.append(row)
    return rows


def _drawdown_from_trades(initial: float, trades: Sequence[dict]) -> float:
    equity = float(initial)
    peak = equity
    worst = 0.0
    for trade in trades:
        equity += float(trade.get("pnl", 0.0))
        peak = max(peak, equity)
        if peak > 0:
            worst = max(worst, (peak - equity) / peak)
    return round(worst * 100, 2)


def _regime_proxy(rows: Sequence[dict]) -> str:
    if len(rows) < 2:
        return "UNKNOWN"
    first = float(rows[0]["close"])
    last = float(rows[-1]["close"])
    change = (last / first) - 1 if first else 0.0
    if change >= 0.10:
        return "BULL"
    if change <= -0.10:
        return "BEAR"
    return "SIDEWAYS"


def run_multi_stock_research(
    symbols: Sequence[str],
    interval: str = "5",
    initial_capital: float = 100000.0,
    store: ResearchStore = research_store,
) -> dict:
    """Run the untouched baseline strategy across stored NSE datasets.

    This is a ranking/reporting layer, not an optimizer. Missing datasets are
    reported rather than silently downloaded or excluded.
    """
    if interval not in {"1", "5", "15", "25", "60"}:
        raise ValueError("interval must be 1, 5, 15, 25, or 60 minutes")
    requested = list(dict.fromkeys(s.strip().upper() for s in symbols if s.strip()))
    if not requested:
        raise ValueError("At least one symbol is required")

    results = []
    missing = []
    for symbol in requested:
        rows = _rows(store, symbol, interval)
        if not rows:
            missing.append(symbol)
            continue
        result = run_intraday_backtest(rows, IntradayBacktestConfig(initial_capital=initial_capital))
        detail = result.get("trades_detail", [])
        results.append({
            "symbol": symbol,
            "bars": len(rows),
            "years": sorted({_year(row) for row in rows}),
            "regime_proxy": _regime_proxy(rows),
            "return_percent": result["return_percent"],
            "trades": result["trades"],
            "win_rate_percent": result["win_rate_percent"],
            "profit_factor": result["profit_factor"],
            "max_drawdown_percent": _drawdown_from_trades(initial_capital, detail),
            "net_pnl": round(result["ending_capital"] - initial_capital, 2),
        })

    results.sort(key=lambda item: (item["profit_factor"] is not None, item["profit_factor"] or -1, item["return_percent"]), reverse=True)
    return {
        "status": "OK",
        "method": "multi_stock_baseline_no_optimization",
        "interval": interval,
        "requested": requested,
        "tested": len(results),
        "missing_datasets": missing,
        "results": results,
        "warnings": ["regime_proxy uses the tested stock's own period return; it is not a NIFTY market-regime classification."],
    }
