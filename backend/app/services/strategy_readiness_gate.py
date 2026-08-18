from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import sqrt
from typing import Iterable, Any

from app.models.paper_trade import PaperTrade
from app.services.paper_backtest_divergence import compare_backtest_to_paper


@dataclass(frozen=True)
class StrategyReadinessPolicy:
    min_cross_stock_robust_percent: float = 60.0
    min_paper_trades: int = 30
    min_profit_factor: float = 1.10
    max_drawdown_percent: float = 10.0
    max_consecutive_losses: int = 5
    min_average_r: float = 0.0
    min_profitable_regime_windows: int = 2
    regime_windows: int = 3
    min_regime_profit_factor: float = 0.90
    min_statistical_confidence_percent: float = 90.0
    max_return_divergence_percent: float = 10.0
    max_drawdown_divergence_percent: float = 10.0
    evidence_max_age_days: int = 30


def _ordered_closed(trades: Iterable[PaperTrade]) -> list[PaperTrade]:
    return sorted(
        [trade for trade in trades if str(trade.status).upper() == "CLOSED"],
        key=lambda trade: trade.closed_at or trade.created_at,
    )


def _r_values(trades: list[PaperTrade]) -> list[float]:
    values: list[float] = []
    for trade in trades:
        risk = abs(float(trade.entry_price) - float(trade.stop_price)) * abs(int(trade.quantity))
        if risk > 0:
            values.append(float(trade.pnl or 0.0) / risk)
    return values


def _pf(pnls: list[float]) -> float | None:
    wins = sum(p for p in pnls if p > 0)
    losses = abs(sum(p for p in pnls if p < 0))
    return wins / losses if losses else (None if wins == 0 else float("inf"))


def _regime_windows(trades: list[PaperTrade], count: int) -> list[dict[str, Any]]:
    if not trades or count < 1:
        return []
    size = max(1, len(trades) // count)
    windows: list[dict[str, Any]] = []
    for index in range(count):
        start = index * size
        end = len(trades) if index == count - 1 else min(len(trades), (index + 1) * size)
        bucket = trades[start:end]
        if not bucket:
            continue
        pnls = [float(t.pnl or 0.0) for t in bucket]
        windows.append({
            "window": index + 1,
            "trades": len(bucket),
            "pnl": round(sum(pnls), 2),
            "profit_factor": _pf(pnls),
            "positive": sum(pnls) > 0,
            "start": (bucket[0].closed_at or bucket[0].created_at).isoformat() if (bucket[0].closed_at or bucket[0].created_at) else None,
            "end": (bucket[-1].closed_at or bucket[-1].created_at).isoformat() if (bucket[-1].closed_at or bucket[-1].created_at) else None,
        })
    return windows


def _paper_metrics(trades: list[PaperTrade]) -> dict[str, Any]:
    pnls = [float(t.pnl or 0.0) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    equity = peak = 100000.0
    max_dd = 0.0
    consecutive = maximum_consecutive = 0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        if peak:
            max_dd = max(max_dd, (peak - equity) / peak * 100.0)
        if pnl < 0:
            consecutive += 1
            maximum_consecutive = max(maximum_consecutive, consecutive)
        else:
            consecutive = 0
    rs = _r_values(trades)
    mean_r = sum(rs) / len(rs) if rs else None
    if len(rs) > 1 and mean_r is not None:
        variance = sum((value - mean_r) ** 2 for value in rs) / (len(rs) - 1)
        std_error = sqrt(variance / len(rs))
        lower_bound = mean_r - 1.645 * std_error
    else:
        lower_bound = None
    return {
        "trades": len(trades),
        "win_rate_percent": round(len(wins) / len(trades) * 100, 2) if trades else 0.0,
        "profit_factor": _pf(pnls),
        "realized_pnl": round(sum(pnls), 2),
        "max_drawdown_percent": round(max_dd, 2),
        "max_consecutive_losses": maximum_consecutive,
        "average_r": round(mean_r, 4) if mean_r is not None else None,
        "r_lower_confidence_bound": round(lower_bound, 4) if lower_bound is not None else None,
        "statistical_confidence_percent": 90.0,
    }


def evaluate_strategy_readiness(
    *,
    backtest: dict[str, Any],
    research_qualification: dict[str, Any],
    cross_stock_evidence: dict[str, Any],
    paper_trades: Iterable[PaperTrade],
    authorized_fingerprint: str | None,
    reference_now: datetime | None = None,
    policy: StrategyReadinessPolicy = StrategyReadinessPolicy(),
) -> dict[str, Any]:
    """Fail-closed P3 promotion gate. It never authorizes live execution."""
    if policy.regime_windows < 1 or policy.min_profitable_regime_windows > policy.regime_windows:
        raise ValueError("invalid regime policy")
    if not 0 < policy.min_cross_stock_robust_percent <= 100:
        raise ValueError("min_cross_stock_robust_percent must be between 0 and 100")
    now = (reference_now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    closed = _ordered_closed(paper_trades)
    paper = _paper_metrics(closed)
    q = research_qualification.get("qualification", research_qualification)
    robust_percent = float(cross_stock_evidence.get("summary", {}).get("robust_percent") or 0.0)
    current_fingerprint = backtest.get("strategy_fingerprint")
    latest_timestamp = max((trade.closed_at or trade.created_at for trade in closed if trade.closed_at or trade.created_at), default=None)
    evidence_age_days = ((now - latest_timestamp).total_seconds() / 86400.0) if latest_timestamp else None
    divergence = compare_backtest_to_paper(
        backtest,
        {"summary": {**paper, "initial_capital": 100000.0}},
        max_return_gap_percent=policy.max_return_divergence_percent,
        max_drawdown_gap_percent=policy.max_drawdown_divergence_percent,
        min_paper_trades=policy.min_paper_trades,
    )
    regimes = _regime_windows(closed, policy.regime_windows)
    profitable_regimes = sum(1 for item in regimes if item["positive"] and (item["profit_factor"] is None or item["profit_factor"] >= policy.min_regime_profit_factor))

    checks = {
        "research_qualification": q.get("status") == "PAPER_CANDIDATE",
        "cross_stock_consistency": robust_percent >= policy.min_cross_stock_robust_percent,
        "paper_sample": paper["trades"] >= policy.min_paper_trades,
        "paper_profit_factor": paper["profit_factor"] is not None and paper["profit_factor"] >= policy.min_profit_factor,
        "paper_drawdown": paper["max_drawdown_percent"] <= policy.max_drawdown_percent,
        "loss_streak": paper["max_consecutive_losses"] <= policy.max_consecutive_losses,
        "average_r": paper["average_r"] is not None and paper["average_r"] >= policy.min_average_r,
        "statistical_confidence": paper["r_lower_confidence_bound"] is not None and paper["r_lower_confidence_bound"] > policy.min_average_r,
        "regime_stability": len(regimes) == policy.regime_windows and profitable_regimes >= policy.min_profitable_regime_windows,
        "backtest_paper_divergence": divergence["status"] == "WITHIN_EXPECTED_RANGE",
        "parameter_fingerprint_stable": bool(authorized_fingerprint and current_fingerprint and authorized_fingerprint == current_fingerprint),
        "evidence_freshness": evidence_age_days is not None and evidence_age_days <= policy.evidence_max_age_days,
    }

    reasons = [name.upper() + "_FAILED" for name, passed in checks.items() if not passed]
    research_ready = checks["research_qualification"] and checks["cross_stock_consistency"]
    paper_ready = all(checks[name] for name in (
        "paper_sample", "paper_profit_factor", "paper_drawdown", "loss_streak",
        "average_r", "statistical_confidence", "regime_stability",
        "backtest_paper_divergence", "parameter_fingerprint_stable", "evidence_freshness",
    ))
    ready = research_ready and paper_ready
    return {
        "mode": "SIMULATION_ONLY",
        "status": "READY_FOR_STRATEGY_REVIEW" if ready else "NOT_READY",
        "strategy_readiness": ready,
        "paper_trading_allowed": research_ready,
        "live_trading_allowed": False,
        "checks": checks,
        "reasons": reasons,
        "paper": paper,
        "regime_windows": regimes,
        "profitable_regime_windows": profitable_regimes,
        "divergence": divergence,
        "evidence": {
            "latest_trade_timestamp": latest_timestamp.isoformat() if latest_timestamp else None,
            "age_days": round(evidence_age_days, 2) if evidence_age_days is not None else None,
            "max_age_days": policy.evidence_max_age_days,
        },
        "fingerprints": {
            "authorized": authorized_fingerprint,
            "current_backtest": current_fingerprint,
            "match": checks["parameter_fingerprint_stable"],
        },
        "policy": policy.__dict__,
        "promotion": {
            "paper_to_strategy_review": ready,
            "strategy_review_to_live": False,
            "manual_live_unlock_required": True,
        },
    }
