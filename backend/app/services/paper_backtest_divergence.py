from __future__ import annotations

from math import isfinite
from typing import Any


def _pct(value: Any) -> float | None:
    if value is None:
        return None
    value = float(value)
    return value if isfinite(value) else None


def compare_backtest_to_paper(
    backtest: dict[str, Any],
    paper: dict[str, Any],
    *,
    max_return_gap_percent: float = 10.0,
    max_drawdown_gap_percent: float = 10.0,
    min_paper_trades: int = 30,
) -> dict[str, Any]:
    """Compare realized paper evidence with a previously generated backtest.

    This is diagnostic evidence, not a promotion decision. A large divergence
    produces a warning and never authorizes live execution.
    """
    if max_return_gap_percent < 0 or max_drawdown_gap_percent < 0:
        raise ValueError("divergence thresholds must be non-negative")
    if min_paper_trades < 1:
        raise ValueError("min_paper_trades must be positive")

    backtest_metrics = backtest.get("metrics", backtest.get("summary", {}))
    paper_metrics = paper.get("summary", paper)
    backtest_return = _pct(backtest_metrics.get("return_percent"))
    paper_return = _pct(paper_metrics.get("return_percent"))
    if paper_return is None and paper_metrics.get("initial_capital"):
        realized = float(paper_metrics.get("realized_pnl", 0.0))
        paper_return = realized / float(paper_metrics["initial_capital"]) * 100

    backtest_dd = _pct(backtest_metrics.get("max_drawdown_percent"))
    paper_dd = _pct(paper_metrics.get("max_drawdown_percent"))
    return_gap = abs(backtest_return - paper_return) if backtest_return is not None and paper_return is not None else None
    drawdown_gap = abs(backtest_dd - paper_dd) if backtest_dd is not None and paper_dd is not None else None
    paper_trades = int(paper_metrics.get("closed_trades", paper_metrics.get("trades", 0)) or 0)

    warnings: list[str] = []
    if paper_trades < min_paper_trades:
        warnings.append("INSUFFICIENT_PAPER_EVIDENCE")
    if return_gap is not None and return_gap > max_return_gap_percent:
        warnings.append("RETURN_DIVERGENCE")
    if drawdown_gap is not None and drawdown_gap > max_drawdown_gap_percent:
        warnings.append("DRAWDOWN_DIVERGENCE")
    if backtest_return is None or paper_return is None:
        warnings.append("MISSING_RETURN_METRIC")

    return {
        "status": "DIVERGENCE_WARNING" if warnings else "WITHIN_EXPECTED_RANGE",
        "live_execution_authorized": False,
        "paper_trade_count": paper_trades,
        "backtest_return_percent": backtest_return,
        "paper_return_percent": paper_return,
        "return_gap_percent": round(return_gap, 4) if return_gap is not None else None,
        "backtest_max_drawdown_percent": backtest_dd,
        "paper_max_drawdown_percent": paper_dd,
        "drawdown_gap_percent": round(drawdown_gap, 4) if drawdown_gap is not None else None,
        "thresholds": {
            "max_return_gap_percent": max_return_gap_percent,
            "max_drawdown_gap_percent": max_drawdown_gap_percent,
            "min_paper_trades": min_paper_trades,
        },
        "warnings": warnings,
    }
