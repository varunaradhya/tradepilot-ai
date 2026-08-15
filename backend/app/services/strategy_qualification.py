from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QualificationPolicy:
    min_trades: int = 30
    min_profit_factor: float = 1.10
    min_positive_return_percent: float = 60.0
    min_pf_above_one_percent: float = 60.0
    max_drawdown_percent: float = 15.0
    min_walk_forward_success_percent: float = 55.0
    require_walk_forward: bool = True


def qualify_strategy(
    backtest: dict,
    robustness: dict,
    walk_forward: dict | None,
    policy: QualificationPolicy = QualificationPolicy(),
) -> dict:
    """Apply a conservative research gate. This never optimizes parameters or places orders."""
    checks: list[dict] = []
    trades = int(backtest.get("trades", 0))
    pf = backtest.get("profit_factor")
    drawdown = float(backtest.get("max_drawdown_percent", 0.0))
    summary = robustness.get("summary", {})

    def check(name: str, passed: bool, actual: object, threshold: object, reason: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "actual": actual, "threshold": threshold, "reason": reason})

    check("minimum_trade_count", trades >= policy.min_trades, trades, policy.min_trades, "Enough trades are required before trusting the sample.")
    check("profit_factor", pf is not None and float(pf) >= policy.min_profit_factor, pf, policy.min_profit_factor, "Profit factor must clear the research floor.")
    check("drawdown", drawdown <= policy.max_drawdown_percent, drawdown, policy.max_drawdown_percent, "Drawdown must remain within the risk ceiling.")
    check("positive_sensitivity", float(summary.get("positive_return_percent", 0.0)) >= policy.min_positive_return_percent, summary.get("positive_return_percent", 0.0), policy.min_positive_return_percent, "Most local sensitivity variants should remain profitable.")
    check("stable_profit_factor", float(summary.get("profit_factor_above_1_percent", 0.0)) >= policy.min_pf_above_one_percent, summary.get("profit_factor_above_1_percent", 0.0), policy.min_pf_above_one_percent, "Most sensitivity variants should retain PF above one.")

    wf_summary = (walk_forward or {}).get("summary", {})
    wf_available = bool(walk_forward) and int(wf_summary.get("window_count", 0)) > 0
    wf_success = float(wf_summary.get("success_rate_percent", 0.0)) if wf_available else 0.0
    check("walk_forward", (not policy.require_walk_forward) or (wf_available and wf_success >= policy.min_walk_forward_success_percent), wf_success if wf_available else None, policy.min_walk_forward_success_percent, "Out-of-sample validation is required before paper trading.")

    passed = all(item["passed"] for item in checks)
    return {
        "status": "PAPER_CANDIDATE" if passed else "NOT_QUALIFIED",
        "paper_trading_allowed": passed,
        "checks": checks,
        "passed_checks": sum(1 for item in checks if item["passed"]),
        "total_checks": len(checks),
        "policy": policy.__dict__,
    }
