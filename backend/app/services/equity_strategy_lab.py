from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class EquityStrategyConfig:
    opening_bars:int=3
    ema_fast:int=20
    ema_slow:int=50
    volume_lookback:int=20
    volume_multiplier:float=1.20
    atr_period:int=14
    stop_atr:float=1.0
    target_atr:float=1.5
    risk_fraction:float=0.005
    slippage_bps:float=5.0
    round_trip_cost_bps:float=12.0
    allow_short:bool=True

def _ema(values,n):
    if len(values)<n:return None
    k=2/(n+1); e=sum(values[:n])/n
    for v in values[n:]:e=v*k+e*(1-k)
    return e

def _atr(highs,lows,closes,n):
    if len(closes)<n+1:return None
    trs=[max(highs[i]-lows[i],abs(highs[i]-closes[i-1]),abs(lows[i]-closes[i-1])) for i in range(1,len(closes))]
    return sum(trs[-n:])/n if len(trs)>=n else None

def _day(ts):
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d') if isinstance(ts,(int,float)) else str(ts)[:10]

def _time(ts):
    if isinstance(ts,(int,float)):return datetime.fromtimestamp(ts).strftime('%H:%M')
    s=str(ts);return s[11:16]

def _group(rows):
    out={}
    for r in rows:out.setdefault(_day(r['timestamp']),[]).append(r)
    for x in out.values():x.sort(key=lambda r:r['timestamp'])
    return out

def _cost(turnover,bps):return turnover*bps/10000

def backtest_orb_momentum(rows,config=EquityStrategyConfig()):
    days=_group(rows); ordered=sorted(rows,key=lambda r:r['timestamp']); trades=[]
    for day,bars in sorted(days.items()):
        if len(bars)<config.opening_bars+2:continue
        first=bars[0]['timestamp']; prior=[r for r in ordered if r['timestamp']<first][-200:]
        if len(prior)<max(config.ema_slow,config.atr_period+1,config.volume_lookback)+2:continue
        orh=max(float(r['high']) for r in bars[:config.opening_bars]);orl=min(float(r['low']) for r in bars[:config.opening_bars]);entry=None
        for i in range(config.opening_bars,len(bars)):
            hist=prior+bars[:i+1]; closes=[float(r['close']) for r in hist]; highs=[float(r['high']) for r in hist]; lows=[float(r['low']) for r in hist]
            ef=_ema(closes,config.ema_fast);es=_ema(closes,config.ema_slow);atr=_atr(highs,lows,closes,config.atr_period)
            vols=[float(r.get('volume') or 0) for r in hist[-(config.volume_lookback+1):]]
            if None in (ef,es,atr) or atr<=0 or len(vols)<config.volume_lookback+1:continue
            rv=vols[-1]/(sum(vols[:-1])/config.volume_lookback) if sum(vols[:-1])>0 else 0; price=float(bars[i]['close'])
            if _time(bars[i]['timestamp'])<'09:30':continue
            if price>orh and price>ef>es and rv>=config.volume_multiplier:entry=('LONG',bars[i],atr);break
            if config.allow_short and price<orl and price<ef<es and rv>=config.volume_multiplier:entry=('SHORT',bars[i],atr);break
        if not entry:continue
        side,eb,atr=entry; ep=float(eb['close']);stop=ep-atr*config.stop_atr if side=='LONG' else ep+atr*config.stop_atr;target=ep+atr*config.target_atr if side=='LONG' else ep-atr*config.target_atr;future=bars[bars.index(eb)+1:];xr=future[-1];reason='EOD'
        for b in future:
            if side=='LONG':
                if float(b['low'])<=stop:xr=b;reason='STOP';break
                if float(b['high'])>=target:xr=b;reason='TARGET';break
            else:
                if float(b['high'])>=stop:xr=b;reason='STOP';break
                if float(b['low'])<=target:xr=b;reason='TARGET';break
        xp=float(xr['close']); per_share=(xp-ep) if side=='LONG' else (ep-xp); risk_cash=max(100000*config.risk_fraction,1); qty=max(1,int(risk_cash/max(abs(ep-stop),0.01))); turnover=(ep+xp)*qty; gross=per_share*qty; costs=_cost(turnover,config.round_trip_cost_bps);slip=_cost(turnover,config.slippage_bps);trades.append({'date':day,'side':side,'entry':ep,'exit':xp,'quantity':qty,'gross_pnl':gross,'costs':costs,'slippage':slip,'pnl':gross-costs-slip,'exit_reason':reason,'entry_timestamp':eb['timestamp'],'exit_timestamp':xr['timestamp']})
    return trades

def backtest_vwap_mean_reversion(rows,config=EquityStrategyConfig()):
    # Candidate family only: fade an extended move back toward session VWAP.
    days=_group(rows);trades=[]
    for day,bars in sorted(days.items()):
        if len(bars)<20:continue
        cum_pv=cum_v=0.0;vwap=[]
        for b in bars:
            typical=(float(b['high'])+float(b['low'])+float(b['close']))/3;v=float(b.get('volume') or 0);cum_pv+=typical*v;cum_v+=v;vwap.append(cum_pv/cum_v if cum_v else typical)
        entry=None
        for i in range(10,len(bars)-3):
            p=float(bars[i]['close']);vw=vwap[i];atr=_atr([float(x['high']) for x in bars[:i+1]],[float(x['low']) for x in bars[:i+1]],[float(x['close']) for x in bars[:i+1]],config.atr_period)
            if not atr or _time(bars[i]['timestamp'])<'09:45':continue
            if p<vw-atr:entry=('LONG',i,atr);break
            if config.allow_short and p>vw+atr:entry=('SHORT',i,atr);break
        if not entry:continue
        side,i,atr=entry;ep=float(bars[i]['close']);target=vwap[i];stop=ep-atr if side=='LONG' else ep+atr;xr=bars[-1];reason='EOD'
        for b in bars[i+1:]:
            if side=='LONG' and float(b['low'])<=stop:xr=b;reason='STOP';break
            if side=='SHORT' and float(b['high'])>=stop:xr=b;reason='STOP';break
            if side=='LONG' and float(b['high'])>=target:xr=b;reason='VWAP';break
            if side=='SHORT' and float(b['low'])<=target:xr=b;reason='VWAP';break
        xp=float(xr['close']);per_share=(xp-ep) if side=='LONG' else (ep-xp);qty=max(1,int(100000*config.risk_fraction/max(abs(ep-stop),0.01)));turnover=(ep+xp)*qty;gross=per_share*qty;trades.append({'date':day,'side':side,'entry':ep,'exit':xp,'quantity':qty,'gross_pnl':gross,'costs':_cost(turnover,config.round_trip_cost_bps),'slippage':_cost(turnover,config.slippage_bps),'pnl':gross-_cost(turnover,config.round_trip_cost_bps)-_cost(turnover,config.slippage_bps),'exit_reason':reason,'entry_timestamp':bars[i]['timestamp'],'exit_timestamp':xr['timestamp']})
    return trades

def summarize(trades):
    pnl=[float(t['pnl']) for t in trades];wins=[x for x in pnl if x>0];losses=[x for x in pnl if x<0];eq=peak=dd=0.0
    yearly={}
    for t in trades:yearly[t['date'][:4]]=yearly.get(t['date'][:4],0.0)+float(t['pnl'])
    for x in pnl:eq+=x;peak=max(peak,eq);dd=max(dd,peak-eq)
    gl=abs(sum(losses));return {'trades':len(pnl),'wins':len(wins),'losses':len(losses),'win_rate_percent':len(wins)/len(pnl)*100 if pnl else 0.0,'net_pnl':sum(pnl),'profit_factor':sum(wins)/gl if gl else None,'expectancy_per_trade':sum(pnl)/len(pnl) if pnl else 0.0,'max_drawdown':dd,'positive_years':sum(v>0 for v in yearly.values()),'yearly_pnl':yearly}
