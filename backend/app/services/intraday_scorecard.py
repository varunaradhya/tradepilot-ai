from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest
from app.services.intraday_research_lab import run_research_lab


@dataclass(frozen=True)
class ScorecardConfig:
    initial_capital: float = 100000.0
    minimum_trades: int = 20
    slippage_rate: float = 0.001


def build_intraday_scorecard(datasets: dict[str, Sequence[dict]], config: ScorecardConfig = ScorecardConfig()) -> dict:
    """Rank datasets using fixed execution assumptions; never tune parameters."""
    if not datasets:
        return {"status": "NO_DATA", "ranked": []}
    ranked = []
    for symbol, rows in datasets.items():
        symbol = symbol.strip().upper()
        if not rows:
            ranked.append({"symbol": symbol, "status": "NO_DATA"})
            continue
        bt = run_intraday_backtest(rows, IntradayBacktestConfig(initial_capital=config.initial_capital, slippage_rate=config.slippage_rate))
        metrics = {k: v for k, v in bt.items() if k != "trades_detail"}
        lab = run_research_lab(rows)
        reasons = []
        trades = int(metrics.get("trades", 0))
        pf = float(metrics.get("profit_factor") or 0)
        expectancy = float(metrics.get("expectancy") or 0)
        dd = float(metrics.get("max_drawdown_percent") or 0)
        if trades < config.minimum_trades: reasons.append("INSUFFICIENT_TRADES")
        if pf <= 1: reasons.append("NO_POSITIVE_PROFIT_FACTOR")
        if expectancy <= 0: reasons.append("NON_POSITIVE_EXPECTANCY")
        if dd > 10: reasons.append("HIGH_DRAWDOWN")
        stressed = next((x for x in lab.get("slippage_sensitivity", []) if abs(float(x.get("slippage_rate", 0)) - 0.001) < 1e-12), None)
        if stressed and float(stressed.get("profit_factor") or 0) <= 1: reasons.append("FRAGILE_TO_SLIPPAGE")
        robustness = "ROBUST" if not reasons else "NEEDS_REVIEW"
        score = round(pf * 40 + min(max(expectancy, -1000), 1000) / 1000 * 20 + max(0, 20 - dd * 2) + min(trades, 20) / 20 * 20, 2)
        ranked.append({"symbol": symbol, "metrics": metrics, "robustness": {"status": robustness, "reasons": reasons}, "research": lab, "score": score})
    ranked.sort(key=lambda x: x.get("score", float("-inf")), reverse=True)
    return {"status": "OK", "assumptions": {"initial_capital": config.initial_capital, "slippage_rate": config.slippage_rate, "minimum_trades": config.minimum_trades, "parameter_selection": False}, "ranked": ranked}
