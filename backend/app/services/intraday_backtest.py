from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.services.execution_model import ExecutionModelConfig
from app.services.intraday_strategy import IntradayConfig, generate_intraday_signal
from app.services.intraday_strategy_v2 import IntradayV2Config, generate_intraday_v2_signal
from app.services.strategy_identity import strategy_fingerprint

@dataclass(frozen=True)
class IntradayBacktestConfig:
    initial_capital: float = 100000.0
    brokerage_rate: float = 0.0003
    slippage_rate: float = 0.0005
    spread_bps: float = 0.0
    market_impact_bps: float = 0.0
    impact_reference_value: float = 100000.0
    max_volume_participation: float = 0.0
    max_daily_loss_percent: float = 1.0
    max_trades_per_session: int = 3
    strategy: IntradayConfig = IntradayConfig()
    strategy_version: str = "V1"

def _metrics(initial_capital: float, ending_capital: float, trades: list[dict]) -> dict:
    pnls=[float(t["pnl"]) for t in trades]; wins=[p for p in pnls if p>0]; losses=[p for p in pnls if p<0]
    gross=[float(t.get("gross_pnl",p)) for t,p in zip(trades,pnls)]; costs=sum(float(t.get("total_costs",0)) for t in trades)
    equity=peak=float(initial_capital); dd=0.0
    for p in pnls:
        equity+=p; peak=max(peak,equity); dd=max(dd,(peak-equity)/peak*100 if peak else 0)
    return {"initial_capital":round(initial_capital,2),"ending_capital":round(ending_capital,2),"return_percent":round((ending_capital/initial_capital-1)*100,2) if initial_capital else 0.0,"trades":len(trades),"wins":len(wins),"losses":len(losses),"win_rate_percent":round(len(wins)/len(trades)*100,2) if trades else 0.0,"profit_factor":round(sum(wins)/abs(sum(losses)),4) if losses else None,"expectancy":round(sum(pnls)/len(pnls),4) if pnls else 0.0,"average_win":round(sum(wins)/len(wins),4) if wins else 0.0,"average_loss":round(sum(losses)/len(losses),4) if losses else 0.0,"max_drawdown_percent":round(dd,2),"gross_pnl":round(sum(gross),2),"total_costs":round(costs,2),"cost_drag_percent":round(costs/initial_capital*100,4) if initial_capital else 0.0}

def run_intraday_backtest(rows: Sequence[dict], config: IntradayBacktestConfig = IntradayBacktestConfig()) -> dict:
    """Single-position intraday research backtest with explicit executable-fill assumptions."""
    if config.strategy.trade_direction not in {"LONG_ONLY","LONG_SHORT"}: raise ValueError("trade_direction must be LONG_ONLY or LONG_SHORT")
    if config.strategy_version not in {"V1","V2"}: raise ValueError("strategy_version must be V1 or V2")
    execution=ExecutionModelConfig(config.brokerage_rate,config.slippage_rate,config.spread_bps,config.market_impact_bps,config.impact_reference_value,config.max_volume_participation)
    identity=strategy_fingerprint(config.strategy,strategy_version=config.strategy_version,execution={"initial_capital":config.initial_capital,"max_daily_loss_percent":config.max_daily_loss_percent,"max_trades_per_session":config.max_trades_per_session,**execution.fingerprint_dict()})
    if not rows: return _metrics(config.initial_capital,config.initial_capital,[])|{"trades_detail":[],"strategy_version":config.strategy_version,"trade_direction":config.strategy.trade_direction,"strategy_fingerprint":identity}
    cash=float(config.initial_capital); trades=[]; position=None; current_session=None; session_rows=[]; session_start_cash=cash; session_pnl=0.0; session_trade_count=0; session_halted=False
    def close_position(reference:float,reason:str,time=None,gap_open=None):
        nonlocal cash,position,session_pnl
        if position is None:return
        qty=position["quantity"]; ref=gap_open if gap_open is not None else reference; exit_price=execution.fill_price(ref,"SELL",qty*ref); exit_cost=execution.commission(qty*exit_price); cash+=qty*exit_price-exit_cost
        gross_pnl=qty*(ref-position["signal_entry"]); pnl=qty*(exit_price-position["entry"])-exit_cost-position["entry_cost"]; costs=position["entry_cost"]+exit_cost
        trade={"entry":position["entry"],"exit":exit_price,"signal_entry":position["signal_entry"],"quantity":qty,"pnl":pnl,"gross_pnl":gross_pnl,"entry_cost":position["entry_cost"],"exit_cost":exit_cost,"total_costs":costs,"reason":reason,"direction":"LONG"}
        if position.get("entry_time") is not None:trade["entry_time"]=position["entry_time"]
        if time is not None:trade["exit_time"]=time
        if gap_open is not None:trade["gap_fill"]=True
        session_pnl+=pnl; trades.append(trade); position=None
    for i,row in enumerate(rows):
        session=row.get("session")
        if session is not None and current_session is not None and session!=current_session:
            if position is not None:close_position(float(rows[i-1]["close"]),"SESSION_CLOSE",rows[i-1].get("timestamp",rows[i-1].get("time")))
            session_rows=[]; session_start_cash=cash; session_pnl=0.0; session_trade_count=0; session_halted=False
        current_session=session; session_rows.append(row)
        if position is not None:
            high,low,op=float(row["high"]),float(row["low"]),float(row["open"])
            if low<=position["stop"]: close_position(position["stop"],"STOP_GAP" if op<=position["stop"] else "STOP",row.get("timestamp",row.get("time")),op if op<=position["stop"] else None)
            elif high>=position["target"]: close_position(position["target"],"TARGET_GAP" if op>=position["target"] else "TARGET",row.get("timestamp",row.get("time")),op if op>=position["target"] else None)
            if session_start_cash and -session_pnl/session_start_cash*100>=config.max_daily_loss_percent:session_halted=True
            if position is not None:continue
        if session_start_cash and -session_pnl/session_start_cash*100>=config.max_daily_loss_percent:session_halted=True
        if session_halted or session_trade_count>=config.max_trades_per_session:continue
        minimum=max(config.strategy.slow_period,config.strategy.volume_period,config.strategy.atr_period+1)
        if len(session_rows)<minimum:continue
        o=[float(x["open"]) for x in session_rows];h=[float(x["high"]) for x in session_rows];l=[float(x["low"]) for x in session_rows];c=[float(x["close"]) for x in session_rows];v=[float(x["volume"]) for x in session_rows];opening=session_rows[:config.strategy.opening_bars]
        if config.strategy_version=="V2":
            v2=config.strategy if isinstance(config.strategy,IntradayV2Config) else IntradayV2Config(**config.strategy.__dict__)
            signal=generate_intraday_v2_signal(o,h,l,c,v,market_closes=[float(x["market_close"]) for x in session_rows] if all("market_close" in x for x in session_rows) else None,sector_closes=[float(x["sector_close"]) for x in session_rows] if all("sector_close" in x for x in session_rows) else None,opening_high=max(float(x["high"]) for x in opening),opening_low=min(float(x["low"]) for x in opening),config=v2)
        else: signal=generate_intraday_signal(o,h,l,c,v,opening_high=max(float(x["high"]) for x in opening),opening_low=min(float(x["low"]) for x in opening),config=config.strategy)
        if signal["action"]!="BUY":continue
        signal_entry=float(signal["entry"]); provisional=execution.fill_price(signal_entry,"BUY",cash*config.strategy.max_position_percent); risk=provisional-float(signal["stop"]); risk_budget=cash*config.strategy.risk_per_trade; max_value=cash*config.strategy.max_position_percent
        requested=min(int(risk_budget/risk),int(max_value/provisional)) if risk>0 else 0; qty=execution.max_fill_quantity(requested,float(row["volume"]) if row.get("volume") is not None else None)
        if qty<=0:continue
        entry=execution.fill_price(signal_entry,"BUY",qty*signal_entry); entry_cost=execution.commission(qty*entry); cash-=qty*entry+entry_cost
        position={"entry":entry,"signal_entry":signal_entry,"stop":float(signal["stop"]),"target":float(signal["target"]),"quantity":qty,"entry_cost":entry_cost,"entry_time":row.get("timestamp",row.get("time"))};session_trade_count+=1
    if position is not None:close_position(float(rows[-1]["close"]),"END_OF_TEST",rows[-1].get("timestamp",rows[-1].get("time")))
    return _metrics(config.initial_capital,cash,trades)|{"trades_detail":trades,"strategy_version":config.strategy_version,"trade_direction":config.strategy.trade_direction,"strategy_fingerprint":identity,"execution_model":execution.fingerprint_dict()}
