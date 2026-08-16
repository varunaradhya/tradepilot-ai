from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from .fno_strategy_v1 import FNOORBConfig, _atr
from .option_strategy_v1 import generate_option_signal

@dataclass(frozen=True)
class OptionResearchConfig:
    capital: float = 100000.0
    lot_size: int = 65
    expiry_flag: str = 'WEEK'
    expiry_code: int = 0
    strike: str = 'ATM'
    interval: str = '5'
    sl_atr: float = 1.0
    target_atr: float = 2.0
    slippage_bps: float = 5.0
    round_trip_cost_bps: float = 12.0

def normalize_rolling(payload: dict) -> list[dict]:
    data=payload.get('data',payload) if isinstance(payload,dict) else {}
    rows=[]
    for side in ('ce','pe'):
        d=data.get(side) if isinstance(data,dict) else None
        if not isinstance(d,dict): continue
        keys=('timestamp','open','high','low','close','volume','strike','oi','iv','spot')
        n=max((len(d.get(k,[])) for k in keys if isinstance(d.get(k,[]),list)),default=0)
        for i in range(n):
            if any(i>=len(d.get(k,[])) for k in ('timestamp','open','high','low','close')): continue
            rows.append({'side':side,'timestamp':d['timestamp'][i],'open':d['open'][i],'high':d['high'][i],'low':d['low'][i],'close':d['close'][i],'volume':d.get('volume',[0]*n)[i],'strike':d.get('strike',[None]*n)[i],'oi':d.get('oi',[None]*n)[i],'iv':d.get('iv',[None]*n)[i],'spot':d.get('spot',[None]*n)[i]})
    return rows

def normalize_spot(payload: dict) -> list[dict]:
    data=payload.get('data',payload) if isinstance(payload,dict) else {}
    if not isinstance(data,dict): return []
    keys=('timestamp','open','high','low','close','volume'); n=max((len(data.get(k,[])) for k in keys if isinstance(data.get(k,[]),list)),default=0)
    return [{'timestamp':data['timestamp'][i],'open':data['open'][i],'high':data['high'][i],'low':data['low'][i],'close':data['close'][i],'volume':data.get('volume',[0]*n)[i]} for i in range(n) if all(i<len(data.get(k,[])) for k in ('timestamp','open','high','low','close'))]

def _day(ts) -> str:
    if isinstance(ts,(int,float)): return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    return str(ts)[:10]

def group_by_day(rows: Iterable[dict]) -> dict[str,list[dict]]:
    out={}
    for r in rows: out.setdefault(_day(r['timestamp']),[]).append(r)
    for v in out.values(): v.sort(key=lambda x:x['timestamp'])
    return out

def simulate_option_days(spot_rows:list[dict], option_rows:list[dict], config:OptionResearchConfig=OptionResearchConfig(), strategy_config:FNOORBConfig=FNOORBConfig()) -> list[dict]:
    spots=group_by_day(spot_rows); opts=group_by_day(option_rows); trades=[]
    for day,sb in sorted(spots.items()):
        if day not in opts or len(sb)<35: continue
        for side in ('ce','pe'):
            ob=[x for x in opts[day] if x['side']==side]
            if len(ob)<21: continue
            signal=generate_option_signal(sb,ob,strategy_config)
            if signal.action!='BUY': continue
            entry=ob[-1]; premium=float(entry['close']); strike=entry.get('strike')
            if premium<=0 or strike is None: continue
            locked=[x for x in ob if x.get('strike')==strike and x['timestamp']>=entry['timestamp']]
            hist=[x for x in ob if x.get('strike')==strike and x['timestamp']<=entry['timestamp']]
            if not locked or len(hist)<15: continue
            a=_atr([float(x['high']) for x in hist],[float(x['low']) for x in hist],[float(x['close']) for x in hist],14)
            if not a or a<=0: continue
            stop=max(0.05,premium-a*config.sl_atr); target=premium+a*config.target_atr
            qty=max(0,int(config.capital*strategy_config.risk_per_trade//(max(premium-stop,0.01)*config.lot_size))*config.lot_size)
            if qty<=0: continue
            exit_row=locked[-1]; reason='EOD'
            for bar in locked[1:]:
                if float(bar['low'])<=stop: exit_row=bar; reason='STOP'; break
                if float(bar['high'])>=target: exit_row=bar; reason='TARGET'; break
            exit_price=float(exit_row['close']); gross=(exit_price-premium)*qty; turnover=(premium+exit_price)*qty
            costs=turnover*(config.round_trip_cost_bps/10000.0); slip=turnover*(config.slippage_bps/10000.0); net=gross-costs-slip
            trades.append({'date':day,'option_type':'CE' if side=='ce' else 'PE','strike':strike,'entry':premium,'exit':exit_price,'quantity':qty,'gross_pnl':gross,'costs':costs,'slippage':slip,'pnl':net,'exit_reason':reason,'entry_timestamp':entry['timestamp'],'exit_timestamp':exit_row['timestamp'],'contract_lock':'rolling_strike_proxy'})
            break
    return trades

def summarize(trades:list[dict]) -> dict:
    pnl=[float(t['pnl']) for t in trades]; wins=[x for x in pnl if x>0]; losses=[x for x in pnl if x<0]; equity=peak=maxdd=0.0
    for x in pnl: equity+=x; peak=max(peak,equity); maxdd=max(maxdd,peak-equity)
    gross_win=sum(wins); gross_loss=abs(sum(losses)); pf=gross_win/gross_loss if gross_loss else None
    return {'trades':len(pnl),'wins':len(wins),'losses':len(losses),'win_rate_percent':len(wins)/len(pnl)*100 if pnl else 0.0,'net_pnl':sum(pnl),'profit_factor':pf,'expectancy_per_trade':sum(pnl)/len(pnl) if pnl else 0.0,'max_drawdown':maxdd,'positive_years':len({t['date'][:4] for t in trades if t['pnl']>0})}
