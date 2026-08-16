from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ValidationGate:
    """Promotion gate: failing any required condition blocks live execution."""
    min_trades: int = 250
    min_profit_factor: float = 1.25
    min_expectancy_per_trade: float = 0.0
    max_drawdown_percent: float = 12.0
    min_positive_years: int = 4
    min_test_return_percent: float = 0.0
    min_paper_trading_days: int = 60
    min_paper_profit_factor: float = 1.15
    min_paper_expectancy: float = 0.0


def evaluate_backtest(metrics: dict, yearly_returns: dict[str,float], gate: ValidationGate=ValidationGate()) -> dict:
    trades=int(metrics.get("trades",0)); pf=metrics.get("profit_factor"); exp=float(metrics.get("expectancy_per_trade",0)); dd=float(metrics.get("max_drawdown_percent",999)); ret=float(metrics.get("return_percent",-999)); positive_years=sum(1 for v in yearly_returns.values() if float(v)>0)
    checks={"enough_trades":trades>=gate.min_trades,"profit_factor":pf is not None and float(pf)>=gate.min_profit_factor,"positive_expectancy":exp>gate.min_expectancy_per_trade,"drawdown":dd<=gate.max_drawdown_percent,"positive_years":positive_years>=gate.min_positive_years,"test_return":ret>gate.min_test_return_percent}
    return {"eligible":all(checks.values()),"checks":checks,"positive_years":positive_years}


def evaluate_paper(metrics: dict, trading_days: int, gate: ValidationGate=ValidationGate()) -> dict:
    pf=metrics.get("profit_factor"); exp=float(metrics.get("expectancy_per_trade",0)); checks={"enough_days":trading_days>=gate.min_paper_trading_days,"profit_factor":pf is not None and float(pf)>=gate.min_paper_profit_factor,"positive_expectancy":exp>gate.min_paper_expectancy,"net_profit":float(metrics.get("net_pnl",0))>0}
    return {"eligible":all(checks.values()),"checks":checks}


def final_promotion(backtest_gate:dict,paper_gate:dict,data_quality_ok:bool,fixed_contract_validation_ok:bool)->dict:
    flags={"backtest":backtest_gate.get("eligible"),"paper":paper_gate.get("eligible"),"data_quality":data_quality_ok,"fixed_contract_validation":fixed_contract_validation_ok}
    eligible=all(bool(v) for v in flags.values())
    return {"status":"PROMOTE" if eligible else "REJECT","eligible":eligible,"reasons":[] if eligible else [k for k,v in flags.items() if not v]}
