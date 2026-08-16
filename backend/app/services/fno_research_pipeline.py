from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

from app.services.fno_strategy_v1 import FNOORBConfig, generate_signal

@dataclass(frozen=True)
class ResearchWindow:
    start: date
    end: date


def chunk_date_range(start: date, end: date, days: int=90) -> list[ResearchWindow]:
    if start>=end or days<=0: return []
    out=[]; cur=start
    while cur<end:
        nxt=min(end,cur+timedelta(days=days)); out.append(ResearchWindow(cur,nxt)); cur=nxt
    return out


def _session_groups(rows: list[dict]) -> Iterable[list[dict]]:
    groups={}
    for row in rows:
        ts=row.get("timestamp")
        if ts is None: continue
        day=str(ts)[:10]
        groups.setdefault(day,[]).append(row)
    for day in sorted(groups):
        bars=sorted(groups[day],key=lambda x:x.get("timestamp",0))
        if len(bars)>=10: yield bars


def _trade_from_signal(signal, entry_bar:dict, future_bars:list[dict], config:FNOORBConfig):
    entry=float(entry_bar["open"])*(1+config.slippage_bps/10000) if signal.action=="BUY" else float(entry_bar["open"])*(1-config.slippage_bps/10000)
    stop=float(signal.stop); target=float(signal.target); side=1 if signal.action=="BUY" else -1
    for bar in future_bars:
        high=float(bar["high"]); low=float(bar["low"])
        if side==1:
            if low<=stop: exit_price=stop*(1-config.slippage_bps/10000); reason="STOP"
            elif high>=target: exit_price=target*(1-config.slippage_bps/10000); reason="TARGET"
            else: continue
        else:
            if high>=stop: exit_price=stop*(1+config.slippage_bps/10000); reason="STOP"
            elif low<=target: exit_price=target*(1+config.slippage_bps/10000); reason="TARGET"
            else: continue
        pnl=(exit_price-entry)*side
        pnl-=entry*config.round_trip_cost_bps/20000
        pnl-=exit_price*config.round_trip_cost_bps/20000
        return {"entry":entry,"exit":exit_price,"pnl":pnl,"reason":reason}
    last=float(future_bars[-1]["close"]) if future_bars else entry
    pnl=(last-entry)*side
    pnl-=entry*config.round_trip_cost_bps/20000
    pnl-=last*config.round_trip_cost_bps/20000
    return {"entry":entry,"exit":last,"pnl":pnl,"reason":"SQUARE_OFF"}


def run_v1_backtest(rows:list[dict], config:FNOORBConfig=FNOORBConfig(), initial_capital:float=100000.0, lot_size:int=1)->dict:
    trades=[]; equity=initial_capital; daily={}
    for bars in _session_groups(rows):
        if len(bars)<60: continue
        signal=generate_signal(bars,config)
        if signal.action=="NO_TRADE": continue
        # Signal is evaluated on the completed signal bar; execution is next bar.
        signal_index=len(bars)-1
        if signal_index+1>=len(bars): continue
        trade=_trade_from_signal(signal,bars[signal_index+1],[],config) if False else None
        # Research caller should pass a session with the candidate signal bar before the remaining bars.
        # To avoid look-ahead, evaluate every completed bar after the opening range and execute on the next bar.
        for i in range(max(60,3),len(bars)-1):
            s=generate_signal(bars[:i+1],config)
            if s.action=="NO_TRADE": continue
            trade=_trade_from_signal(s,bars[i+1],bars[i+2:],config)
            if trade:
                risk=abs(s.entry-s.stop) if s.entry and s.stop else 0
                if risk>0:
                    units=max(1,int((equity*config.risk_per_trade)//risk))
                    units=(units//lot_size)*lot_size
                    if units<=0: continue
                    pnl=trade["pnl"]*units; equity+=pnl
                    trade.update({"date":str(bars[i].get("timestamp"))[:10],"action":s.action,"units":units,"pnl":pnl,"score":s.score,"reason":trade["reason"]})
                    trades.append(trade); daily[trade["date"]]=daily.get(trade["date"],0)+pnl
                    break
    wins=[t["pnl"] for t in trades if t["pnl"]>0]; losses=[t["pnl"] for t in trades if t["pnl"]<0]
    gross_profit=sum(wins); gross_loss=abs(sum(losses)); expectancy=(sum(t["pnl"] for t in trades)/len(trades)) if trades else 0
    peak=initial_capital; dd=0
    running=initial_capital
    for t in trades:
        running+=t["pnl"]; peak=max(peak,running); dd=max(dd,(peak-running)/peak*100 if peak else 0)
    return {"initial_capital":initial_capital,"ending_capital":round(running,2),"return_percent":round((running/initial_capital-1)*100,2),"trades":len(trades),"wins":len(wins),"losses":len(losses),"win_rate_percent":round(len(wins)/len(trades)*100,2) if trades else 0,"profit_factor":round(gross_profit/gross_loss,4) if gross_loss else None,"expectancy_per_trade":round(expectancy,4),"max_drawdown_percent":round(dd,2),"trades_detail":trades,"daily_pnl":daily}
