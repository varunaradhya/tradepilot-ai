from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class PaperReadinessPolicy:
    min_trades: int = 100
    min_profit_factor: float = 1.20
    min_expectancy: float = 0.0
    max_drawdown_percent: float = 10.0
    min_positive_walk_forward_ratio: float = 0.60
    require_lookahead_protection: bool = True


def evaluate_paper_readiness(
    metrics: Mapping[str, object],
    walk_forward: Sequence[Mapping[str, object]] | None = None,
    policy: PaperReadinessPolicy = PaperReadinessPolicy(),
) -> dict:
    """Apply conservative gates before a strategy may enter paper trading.

    This is a safety gate, not a claim that the strategy is profitable.
    Missing evidence fails closed.
    """
    trades = int(metrics.get("trades", 0) or 0)
    profit_factor = float(metrics.get("profit_factor", 0.0) or 0.0)
    expectancy = float(metrics.get("expectancy", 0.0) or 0.0)
    drawdown = abs(float(metrics.get("max_drawdown_percent", metrics.get("max_drawdown", 999.0)) or 999.0))
    lookahead = bool(metrics.get("lookahead_bias_protection", False))

    checks = {
        "minimum_trades": trades >= policy.min_trades,
        "profit_factor": profit_factor >= policy.min_profit_factor,
        "positive_expectancy": expectancy > policy.min_expectancy,
        "drawdown_limit": drawdown <= policy.max_drawdown_percent,
        "lookahead_protection": (lookahead if policy.require_lookahead_protection else True),
    }

    if walk_forward is None:
        checks["walk_forward"] = False
        positive_ratio = 0.0
    else:
        windows = list(walk_forward)
        positive = sum(1 for item in windows if float(item.get("return_percent", item.get("return", 0.0)) or 0.0) > 0)
        positive_ratio = positive / len(windows) if windows else 0.0
        checks["walk_forward"] = bool(windows) and positive_ratio >= policy.min_positive_walk_forward_ratio

    passed = all(checks.values())
    return {
        "status": "PAPER_READY" if passed else "NOT_READY",
        "paper_trading_allowed": passed,
        "checks": checks,
        "walk_forward_positive_ratio": round(positive_ratio, 4),
        "policy": {
            "min_trades": policy.min_trades,
            "min_profit_factor": policy.min_profit_factor,
            "min_expectancy": policy.min_expectancy,
            "max_drawdown_percent": policy.max_drawdown_percent,
            "min_positive_walk_forward_ratio": policy.min_positive_walk_forward_ratio,
            "require_lookahead_protection": policy.require_lookahead_protection,
        },
    }
