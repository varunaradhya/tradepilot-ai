from __future__ import annotations

from statistics import mean
from typing import Mapping, Sequence

from app.services.research_metrics import summarize_trades


def _pf(trades: Sequence[Mapping[str, object]]) -> float | None:
    values = [float(t.get("pnl", 0.0)) for t in trades]
    gross_profit = sum(x for x in values if x > 0)
    gross_loss = abs(sum(x for x in values if x < 0))
    if gross_loss:
        return gross_profit / gross_loss
    return float("inf") if gross_profit else None


def _degradation(reference: float | None, current: float | None) -> float | None:
    if reference is None or current is None or reference == 0:
        return None
    return round((current - reference) / abs(reference) * 100, 2)


def build_strategy_evidence(
    backtest: Sequence[Mapping[str, object]],
    oos: Sequence[Mapping[str, object]],
    paper: Sequence[Mapping[str, object]],
    *,
    strategy_version: str,
    fingerprint: str,
    robustness: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Create a compact evidence summary without changing/optimizing strategy parameters."""
    datasets = {"backtest": backtest, "oos": oos, "paper": paper}
    summaries = {name: summarize_trades(rows) for name, rows in datasets.items()}

    pf_backtest = _pf(backtest)
    pf_oos = _pf(oos)
    pf_paper = _pf(paper)
    degradation = {
        "backtest_to_oos_pf_percent": _degradation(pf_backtest, pf_oos),
        "oos_to_paper_pf_percent": _degradation(pf_oos, pf_paper),
        "backtest_to_paper_pf_percent": _degradation(pf_backtest, pf_paper),
    }

    stages = [backtest, oos, paper]
    stage_counts = [len(x) for x in stages]
    evidence_complete = all(stage_counts)
    return {
        "strategy_version": strategy_version,
        "fingerprint": fingerprint,
        "stages": summaries,
        "degradation": degradation,
        "evidence_complete": bool(evidence_complete),
        "robustness": dict(robustness or {}),
        "interpretation": _interpret(degradation, summaries),
    }


def _interpret(degradation: Mapping[str, float | None], summaries: Mapping[str, Mapping[str, object]]) -> str:
    values = [v for v in degradation.values() if v is not None]
    if not values:
        return "INSUFFICIENT_EVIDENCE"
    if any(v <= -25 for v in values):
        return "EDGE_DEGRADING"
    if any(v <= -10 for v in values):
        return "MONITOR_DEGRADATION"
    if all(v >= -10 for v in values) and summaries["paper"]["trades"]:
        return "CONSISTENT_EVIDENCE"
    return "INSUFFICIENT_EVIDENCE"


def regime_scorecard(trades: Sequence[Mapping[str, object]]) -> dict[str, dict[str, object]]:
    """Summarize realized trades by recorded market regime."""
    regimes = ("TRENDING_UP", "SIDEWAYS", "TRENDING_DOWN")
    result: dict[str, dict[str, object]] = {}
    for regime in regimes:
        rows = [t for t in trades if str(t.get("regime", "")) == regime]
        summary = summarize_trades(rows)
        result[regime] = {
            **summary,
            "net_pnl": round(sum(float(t.get("pnl", 0.0)) for t in rows), 2),
            "average_pnl": round(mean([float(t.get("pnl", 0.0)) for t in rows]), 2) if rows else 0.0,
            "profit_factor": _pf(rows),
        }
    return result
