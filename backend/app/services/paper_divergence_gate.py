from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PaperDivergenceConfig:
    max_profit_factor_degradation_pct: float = 30.0
    max_expectancy_degradation_pct: float = 40.0
    max_drawdown_increase_pct_points: float = 5.0
    min_paper_trades: int = 30


def evaluate_backtest_vs_paper(
    historical: dict,
    paper: dict,
    config: PaperDivergenceConfig = PaperDivergenceConfig(),
) -> dict:
    """Fail-closed comparison of qualified historical evidence and paper evidence."""
    reasons: list[str] = []
    paper_trades = int(paper.get("trades", 0) or 0)
    if paper_trades < config.min_paper_trades:
        reasons.append("INSUFFICIENT_PAPER_TRADES")

    hist_pf = float(historical.get("profit_factor") or 0.0)
    paper_pf = float(paper.get("profit_factor") or 0.0)
    if hist_pf > 0 and paper_pf < hist_pf * (1 - config.max_profit_factor_degradation_pct / 100):
        reasons.append("PROFIT_FACTOR_DEGRADATION")

    hist_exp = float(historical.get("expectancy") or 0.0)
    paper_exp = float(paper.get("expectancy") or 0.0)
    if hist_exp > 0 and paper_exp < hist_exp * (1 - config.max_expectancy_degradation_pct / 100):
        reasons.append("EXPECTANCY_DEGRADATION")
    if hist_exp > 0 and paper_exp <= 0:
        reasons.append("NON_POSITIVE_PAPER_EXPECTANCY")

    hist_dd = float(historical.get("max_drawdown_percent") or 0.0)
    paper_dd = float(paper.get("max_drawdown_percent") or 0.0)
    if paper_dd > hist_dd + config.max_drawdown_increase_pct_points:
        reasons.append("DRAWDOWN_DEGRADATION")

    return {
        "status": "PASS" if not reasons else "NOT_READY",
        "reasons": reasons,
        "historical": {
            "profit_factor": hist_pf,
            "expectancy": hist_exp,
            "max_drawdown_percent": hist_dd,
        },
        "paper": {
            "trades": paper_trades,
            "profit_factor": paper_pf,
            "expectancy": paper_exp,
            "max_drawdown_percent": paper_dd,
        },
        "rules": {
            "max_profit_factor_degradation_pct": config.max_profit_factor_degradation_pct,
            "max_expectancy_degradation_pct": config.max_expectancy_degradation_pct,
            "max_drawdown_increase_pct_points": config.max_drawdown_increase_pct_points,
            "min_paper_trades": config.min_paper_trades,
        },
    }
