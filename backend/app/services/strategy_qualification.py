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
    min_walk_forward_windows: int = 3
    min_validation_trades_per_window: int = 5
    min_validation_trades_total: int = 30
    max_walk_forward_drawdown_percent: float = 15.0
    require_walk_forward: bool = True


def qualify_strategy(backtest: dict, robustness: dict, walk_forward: dict | None, policy: QualificationPolicy = QualificationPolicy()) -> dict:
    """Apply a conservative, fail-closed research gate.

    A strategy cannot become a paper candidate from a profitable aggregate backtest
    alone. Out-of-sample evidence must contain enough independent validation windows
    and enough validation trades, with bounded drawdown and a passing window rate.
    """
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

    wf = walk_forward or {}
    wf_summary = wf.get("v2", {}).get("summary", {}) if wf else {}
    wf_windows = int(wf.get("windows", 0) or 0)
    wf_available = wf_windows > 0
    wf_success = float(wf_summary.get("success_rate_percent", 0.0)) if wf_available else 0.0
    wf_trades = sum(int(window.get("trades", 0) or 0) for window in wf.get("v2", {}).get("windows", [])) if wf_available else 0
    window_trade_floor = all(int(window.get("trades", 0) or 0) >= policy.min_validation_trades_per_window for window in wf.get("v2", {}).get("windows", [])) if wf_available else False
    wf_max_drawdown = float(wf_summary.get("max_drawdown_percent", 0.0) or 0.0) if wf_available else 0.0

    check("walk_forward_available", (not policy.require_walk_forward) or wf_available, wf_windows, 1, "Chronological out-of-sample validation is required before paper trading.")
    check("walk_forward_window_count", (not policy.require_walk_forward) or (wf_windows >= policy.min_walk_forward_windows), wf_windows, policy.min_walk_forward_windows, "A single validation window is too easy to overfit; multiple windows are required.")
    check("walk_forward_success_rate", (not policy.require_walk_forward) or (wf_available and wf_success >= policy.min_walk_forward_success_percent), wf_success if wf_available else None, policy.min_walk_forward_success_percent, "Most validation windows must remain profitable out of sample.")
    check("walk_forward_trade_count", (not policy.require_walk_forward) or (wf_trades >= policy.min_validation_trades_total), wf_trades, policy.min_validation_trades_total, "Validation evidence must contain enough executed trades to be meaningful.")
    check("walk_forward_window_trade_floor", (not policy.require_walk_forward) or (wf_available and window_trade_floor), [int(window.get("trades", 0) or 0) for window in wf.get("v2", {}).get("windows", [])], policy.min_validation_trades_per_window, "Every validation window must contribute a meaningful trade sample.")
    check("walk_forward_drawdown", (not policy.require_walk_forward) or (wf_available and wf_max_drawdown <= policy.max_walk_forward_drawdown_percent), wf_max_drawdown if wf_available else None, policy.max_walk_forward_drawdown_percent, "Worst validation-window drawdown must stay within the research ceiling.")

    passed = all(item["passed"] for item in checks)
    return {"status": "PAPER_CANDIDATE" if passed else "NOT_QUALIFIED", "paper_trading_allowed": passed, "checks": checks, "passed_checks": sum(1 for item in checks if item["passed"]), "total_checks": len(checks), "policy": policy.__dict__}
