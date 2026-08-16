from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ValidationGate:
    """Every condition is mandatory; failure blocks promotion to live trading."""
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


def chronological_split(rows:list[dict], train_fraction:float=0.60, validation_fraction:float=0.20) -> tuple[list[dict],list[dict],list[dict]]:
    if not 0<train_fraction<1 or not 0<=validation_fraction<1 or train_fraction+validation_fraction>=1: raise ValueError("invalid split fractions")
    ordered=sorted(rows,key=lambda r:r.get("timestamp",0)); n=len(ordered); a=int(n*train_fraction); b=int(n*(train_fraction+validation_fraction)); return ordered[:a],ordered[a:b],ordered[b:]


def walk_forward_windows(rows:list[dict], train_bars:int, test_bars:int, step_bars:int|None=None) -> list[tuple[list[dict],list[dict]]]:
    if train_bars<=0 or test_bars<=0: raise ValueError("window sizes must be positive")
    step=step_bars or test_bars; ordered=sorted(rows,key=lambda r:r.get("timestamp",0)); out=[]; start=0
    while start+train_bars+test_bars<=len(ordered):
        out.append((ordered[start:start+train_bars],ordered[start+train_bars:start+train_bars+test_bars])); start+=step
    return out
