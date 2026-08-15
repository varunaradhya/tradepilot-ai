from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.models.paper_trade import PaperTrade


@dataclass(frozen=True)
class ReadinessPolicy:
    min_cross_stock_robust_percent: float = 60.0
    min_paper_trades: int = 30
    min_paper_profit_factor: float = 1.05
    max_paper_drawdown_percent: float = 10.0
    max_consecutive_losses: int = 5
    min_average_r: float = 0.0


def _paper_metrics(trades: Iterable[PaperTrade]) -> dict:
    closed = [t for t in trades if t.status == "CLOSED"]
    pnls = [float(t.pnl or 0.0) for t in closed]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_loss = abs(sum(losses))
    equity = 100000.0
    peak = equity
    max_dd = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        if peak:
            max_dd = max(max_dd, (peak - equity) / peak * 100)

    r_values: list[float] = []
    hold_minutes: list[float] = []
    exit_reasons: dict[str, int] = {}
    max_consecutive_losses = 0
    consecutive_losses = 0
    for trade, pnl in zip(closed, pnls):
        entry = getattr(trade, "entry_price", None)
        stop = getattr(trade, "stop_price", None)
        quantity = getattr(trade, "quantity", None)
        if entry is not None and stop is not None and quantity is not None:
            risk_per_trade = abs(float(entry) - float(stop)) * abs(int(quantity))
            if risk_per_trade > 0:
                r_values.append(pnl / risk_per_trade)
        created_at = getattr(trade, "created_at", None)
        closed_at = getattr(trade, "closed_at", None)
        if created_at is not None and closed_at is not None:
            seconds = (closed_at - created_at).total_seconds()
            if seconds >= 0:
                hold_minutes.append(seconds / 60.0)
        reason = str(getattr(trade, "reason", None) or "UNKNOWN").upper()
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        if pnl < 0:
            consecutive_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        else:
            consecutive_losses = 0

    average_r = sum(r_values) / len(r_values) if r_values else None
    average_hold = sum(hold_minutes) / len(hold_minutes) if hold_minutes else None
    return {
        "trades": len(closed), "wins": len(wins), "losses": len(losses),
        "win_rate_percent": round(len(wins) / len(closed) * 100, 2) if closed else 0.0,
        "profit_factor": round(sum(wins) / gross_loss, 4) if gross_loss else None,
        "realized_pnl": round(sum(pnls), 2), "max_drawdown_percent": round(max_dd, 2),
        "average_r": round(average_r, 4) if average_r is not None else None,
        "average_hold_minutes": round(average_hold, 2) if average_hold is not None else None,
        "max_consecutive_losses": max_consecutive_losses,
        "exit_reasons": dict(sorted(exit_reasons.items())),
    }


def build_strategy_readiness(
    qualification: dict,
    cross_stock_evidence: dict,
    paper_trades: Iterable[PaperTrade],
    policy: ReadinessPolicy = ReadinessPolicy(),
) -> dict:
    paper = _paper_metrics(paper_trades)
    q = qualification.get("qualification", qualification)
    q_status = str(q.get("status", "NOT_QUALIFIED"))
    robust_percent = float(cross_stock_evidence.get("summary", {}).get("robust_percent") or 0.0)
    sample_complete = paper["trades"] >= policy.min_paper_trades
    checks = {
        "research_qualification": q_status == "PAPER_CANDIDATE",
        "cross_stock_consistency": robust_percent >= policy.min_cross_stock_robust_percent,
        "paper_trade_sample": sample_complete,
        "paper_profit_factor": paper["profit_factor"] is not None and paper["profit_factor"] >= policy.min_paper_profit_factor,
        "paper_drawdown": paper["max_drawdown_percent"] <= policy.max_paper_drawdown_percent,
        "paper_risk_quality": (
            not sample_complete or (
                (paper["average_r"] is None or paper["average_r"] >= policy.min_average_r)
                and paper["max_consecutive_losses"] <= policy.max_consecutive_losses
            )
        ),
    }
    reasons: list[str] = []
    if not checks["research_qualification"]:
        reasons.append("RESEARCH_QUALIFICATION_FAILED")
    if not checks["cross_stock_consistency"]:
        reasons.append("CROSS_STOCK_EVIDENCE_INSUFFICIENT")
    if not checks["paper_trade_sample"]:
        reasons.append("PAPER_TRADE_SAMPLE_INSUFFICIENT")
    if sample_complete and not checks["paper_profit_factor"]:
        reasons.append("PAPER_PROFIT_FACTOR_TOO_LOW")
    if sample_complete and not checks["paper_drawdown"]:
        reasons.append("PAPER_DRAWDOWN_TOO_HIGH")
    if sample_complete and not checks["paper_risk_quality"]:
        reasons.append("PAPER_RISK_QUALITY_FAILED")

    research_ready = checks["research_qualification"] and checks["cross_stock_consistency"]
    paper_ready = checks["paper_trade_sample"] and checks["paper_profit_factor"] and checks["paper_drawdown"] and checks["paper_risk_quality"]
    status = "LIVE_REVIEW" if research_ready and paper_ready else "PAPER_VALIDATION" if research_ready else "NOT_READY"
    return {
        "status": status,
        "live_trading_allowed": False,
        "paper_trading_allowed": research_ready,
        "checks": checks,
        "reasons": reasons,
        "paper": paper,
        "cross_stock": {"robust_percent": round(robust_percent, 2), "symbols_tested": int(cross_stock_evidence.get("summary", {}).get("symbols_tested") or 0)},
        "policy": {
            "min_cross_stock_robust_percent": policy.min_cross_stock_robust_percent,
            "min_paper_trades": policy.min_paper_trades,
            "min_paper_profit_factor": policy.min_paper_profit_factor,
            "max_paper_drawdown_percent": policy.max_paper_drawdown_percent,
            "max_consecutive_losses": policy.max_consecutive_losses,
            "min_average_r": policy.min_average_r,
        },
        "research_policy": {"parameter_selection": False, "live_execution": False},
    }
