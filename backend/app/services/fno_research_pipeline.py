from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Iterable
from zoneinfo import ZoneInfo
from app.services.fno_strategy_v1 import FNOORBConfig, generate_signal
IST=ZoneInfo("Asia/Kolkata")
@dataclass(frozen=True)
class ResearchWindow:
    start: date
    end: date

def chunk_date_range(start: date,end: date,days: int=90)->list[ResearchWindow]:
    if start>=end or days<=0:return []
    out=[];cur=start
    while cur<end:
        nxt=min(end,cur+timedelta(days=days));out.append(ResearchWindow(cur,nxt));cur=nxt
    return out

def _session_day(ts)->str:
    if isinstance(ts,(int,float)):return datetime.fromtimestamp(float(ts),tz=timezone.utc).astimezone(IST).date().isoformat()
    return str(ts)[:10]

def _session_groups(rows:list[dict])->Iterable[list[dict]]:
    groups={}
    for row in rows:
        ts=row.get("timestamp")
        if ts is not None:groups.setdefault(_session_day(ts),[]).append(row)
    for day in sorted(groups):
        bars=sorted(groups[day],key=lambda x:x.get("timestamp",0))
        if len(bars)>=60:yield bars

def validate_bars(rows:list[dict])->dict:
    ts=[r.get("timestamp") for r in rows if r.get("timestamp") is not None]
    dup=len(ts)-len(set(ts)); invalid=sum(1 for r in rows if any(r.get(k) is None for k in ("open","high","low","close","timestamp")))
    sessions=sum(1 for _ in _session_groups(rows))
    return {"bars":len(rows),"unique_timestamps":len(set(ts)),"duplicate_timestamps":dup,"invalid_rows":invalid,"sessions":sessions,"quality_ok":bool(rows) and dup==0 and invalid==0 and sessions>0}

def nifty_lot_size_for_day(day:str)->int:
    # NSE schedule: 25 before 2024-11-21; 75 until 2025-12-30 expiry transition; 65 thereafter.
    if day<"2024-11-21":return 25
    if day<"2025-12-31":return 75
    return 65

def _trade_from_signal(signal,entry_bar:dict,future_bars:list[dict],config:FNOORBConfig):
    if not future_bars:return None
    entry=float(entry_bar["open"])*(1+config.slippage_bps/10000) if signal.action=="BUY" else float(entry_bar["open"])*(1-config.slippage_bps/10000)
    stop=float(signal.stop);target=float(signal.target);side=1 if signal.action=="BUY" else -1
    for bar in future_bars:
        high=float(bar["high"]);low=float(bar["low"])
        if side==1:
            if low<=stop:exit_price=stop*(1-config.slippage_bps/10000);reason="STOP"
            elif high>=target:exit_price=target*(1-config.slippage_bps/10000);reason="TARGET"
            else:continue
        else:
            if high>=stop:exit_price=stop*(1+config.slippage_bps/10000);reason="STOP"
            elif low<=target:exit_price=target*(1+config.slippage_bps/10000);reason="TARGET"
            else:continue
        pnl=(exit_price-entry)*side-(entry+exit_price)*config.round_trip_cost_bps/20000
        return {"entry":entry,"exit":exit_price,"pnl":pnl,"reason":reason}
    last=float(future_bars[-1]["close"]);pnl=(last-entry)*side-(entry+last)*config.round_trip_cost_bps/20000
    return {"entry":entry,"exit":last,"pnl":pnl,"reason":"SQUARE_OFF"}

def run_v1_backtest(rows:list[dict],config:FNOORBConfig=FNOORBConfig(),initial_capital:float=100000.0,lot_size:int|Callable[[str],int]=nifty_lot_size_for_day)->dict:
    trades=[];equity=initial_capital;daily={}
    for bars in _session_groups(rows):
        for i in range(53,len(bars)-1):
            s=generate_signal(bars[:i+1],config)
            if s.action=="NO_TRADE":continue
            trade=_trade_from_signal(s,bars[i+1],bars[i+2:],config)
            if not trade:continue
            actual_entry=trade["entry"];risk=abs(actual_entry-float(s.stop)) if s.stop is not None else 0
            day=_session_day(bars[i].get("timestamp"));lot=int(lot_size(day) if callable(lot_size) else lot_size)
            if risk<=0 or lot<=0:continue
            units=int((equity*config.risk_per_trade)//(risk*lot))*lot
            if units<=0:continue
            pnl=trade["pnl"]*units;equity+=pnl
            trade.update({"date":day,"action":s.action,"units":units,"lot_size":lot,"pnl":pnl,"score":s.score,"reason":trade["reason"]});trades.append(trade);daily[day]=daily.get(day,0)+pnl
            break
    wins=[t["pnl"] for t in trades if t["pnl"]>0];losses=[t["pnl"] for t in trades if t["pnl"]<0];gross_profit=sum(wins);gross_loss=abs(sum(losses));expectancy=sum(t["pnl"] for t in trades)/len(trades) if trades else 0
    peak=initial_capital;dd=0;running=initial_capital
    for t in trades:
        running+=t["pnl"];peak=max(peak,running);dd=max(dd,(peak-running)/peak*100 if peak else 0)
    return {"initial_capital":initial_capital,"ending_capital":round(running,2),"return_percent":round((running/initial_capital-1)*100,2),"trades":len(trades),"wins":len(wins),"losses":len(losses),"win_rate_percent":round(len(wins)/len(trades)*100,2) if trades else 0,"profit_factor":round(gross_profit/gross_loss,4) if gross_loss else None,"expectancy_per_trade":round(expectancy,4),"max_drawdown_percent":round(dd,2),"trades_detail":trades,"daily_pnl":daily}
