from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from .fno_strategy_v1 import FNOORBConfig, _atr
from .option_strategy_v1 import generate_option_signal

@dataclass(frozen=True)
class OptionResearchConfig:
    capital: float=100000.0; lot_size:int=65; expiry_flag:str='WEEK'; expiry_code:int=0; strike:str='ATM'; interval:str='5'; sl_atr:float=1.0; target_atr:float=2.0; slippage_bps:float=5.0; round_trip_cost_bps:float=12.0

def historical_nifty_lot_size(day:str)->int:
    # NSE lot revisions: 25 for new contracts before 2024-11-20; 75 from
    # 2024-11-20; revised 65 from the Oct-2025 revision for applicable new contracts.
    if day<'2024-11-20': return 25
    if day<'2025-10-29': return 75
    return 65

def normalize_rolling(payload:dict)->list[dict]:
    data=payload.get('data',payload) if isinstance(payload,dict) else {}; rows=[]
    for side in ('ce','pe'):
        d=data.get(side) if isinstance(data,dict) else None
        if not isinstance(d,dict): continue
        keys=('timestamp','open','high','low','close','volume','strike','oi','iv','spot'); n=max((len(d.get(k,[])) for k in keys if isinstance(d.get(k,[]),list)),default=0)
        for i in range(n):
            if any(i>=len(d.get(k,[])) for k in ('timestamp','open','high','low','close')): continue
            rows.append({'side':side,'timestamp':d['timestamp'][i],'open':d['open'][i],'high':d['high'][i],'low':d['low'][i],'close':d['close'][i],'volume':d.get('volume',[0]*n)[i],'strike':d.get('strike',[None]*n)[i],'oi':d.get('oi',[None]*n)[i],'iv':d.get('iv',[None]*n)[i],'spot':d.get('spot',[None]*n)[i]})
    return rows

def normalize_spot(payload:dict)->list[dict]:
    data=payload.get('data',payload) if isinstance(payload,dict) else {}
    if not isinstance(data,dict): return []
    keys=('timestamp','open','high','low','close','volume'); n=max((len(data.get(k,[])) for k in keys if isinstance(data.get(k,[]),list)),default=0)
    return [{'timestamp':data['timestamp'][i],'open':data['open'][i],'high':data['high'][i],'low':data['low'][i],'close':data['close'][i],'volume':data.get('volume',[0]*n)[i]} for i in range(n) if all(i<len(data.get(k,[])) for k in ('timestamp','open','high','low','close'))]

def _day(ts)->str:
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d') if isinstance(ts,(int,float)) else str(ts)[:10]

def group_by_day(rows:Iterable[dict])->dict[str,list[dict]]:
    out={}
    for r in rows: out.setdefault(_day(r['timestamp']),[]).append(r)
    for v in out.values(): v.sort(key=lambda x:x['timestamp'])
    return out

def _first_signal(sb:list[dict],ob:list[dict],strategy_config:FNOORBConfig):
    by_ts={x['timestamp']:x for x in ob}; warm=max(strategy_config.ema_slow,strategy_config.rsi_period+1,strategy_config.atr_period+1)+3
    for i in range(warm,len(sb)):
        upto=sb[:i+1]; opt=[x for x in ob if x['timestamp']<=upto[-1]['timestamp']]
        if not opt: continue
        sig=generate_option_signal(upto,opt,strategy_config)
        if sig.action=='BUY':
            entry=by_ts.get(upto[-1]['timestamp'])
            if entry: return entry,sig
    return None,None

def simulate_option_days(spot_rows:list[dict],option_rows:list[dict],config:OptionResearchConfig=OptionResearchConfig(),strategy_config:FNOORBConfig=FNOORBConfig())->list[dict]:
    spots=group_by_day(spot_rows); opts=group_by_day(option_rows); trades=[]
    for day,sb in sorted(spots.items()):
        if day not in opts or len(sb)<35: continue
        for side in ('ce','pe'):
            ob=[x for x in opts[day] if x['side']==side]; entry,signal=_first_signal(sb,ob,strategy_config)
            if not entry: continue
            premium=float(entry['close']); strike=entry.get('strike')
            if premium<=0 or strike is None: continue
            hist=[x for x in ob if x.get('strike')==strike and x['timestamp']<=entry['timestamp']]; future=[x for x in ob if x.get('strike')==strike and x['timestamp']>entry['timestamp']]
            if len(hist)<15 or not future: continue
            a=_atr([float(x['high']) for x in hist],[float(x['low']) for x in hist],[float(x['close']) for x in hist],14)
            if not a or a<=0: continue
            stop=max(0.05,premium-a*config.sl_atr); target=premium+a*config.target_atr; lot=historical_nifty_lot_size(day)
            qty=max(0,int(config.capital*strategy_config.risk_per_trade//(max(premium-stop,0.01)*lot))*lot)
            if qty<=0: continue
            exit_row=future[-1]; reason='EOD'
            for bar in future:
                if float(bar['low'])<=stop: exit_row=bar; reason='STOP'; break
                if float(bar['high'])>=target: exit_row=bar; reason='TARGET'; break
            exit_price=float(exit_row['close']); gross=(exit_price-premium)*qty; turnover=(premium+exit_price)*qty; costs=turnover*(config.round_trip_cost_bps/10000); slip=turnover*(config.slippage_bps/10000); net=gross-costs-slip
            trades.append({'date':day,'option_type':'CE' if side=='ce' else 'PE','strike':strike,'lot_size':lot,'entry':premium,'exit':exit_price,'quantity':qty,'gross_pnl':gross,'costs':costs,'slippage':slip,'pnl':net,'exit_reason':reason,'entry_timestamp':entry['timestamp'],'exit_timestamp':exit_row['timestamp'],'contract_lock':'rolling_strike_proxy','signal_reasons':list(signal.reason)})
            break
    return trades

def summarize(trades:list[dict])->dict:
    pnl=[float(t['pnl']) for t in trades]; wins=[x for x in pnl if x>0]; losses=[x for x in pnl if x<0]; equity=peak=maxdd=0.0
    for x in pnl: equity+=x; peak=max(peak,equity); maxdd=max(maxdd,peak-equity)
    gross_win=sum(wins); gross_loss=abs(sum(losses)); pf=gross_win/gross_loss if gross_loss else None
    return {'trades':len(pnl),'wins':len(wins),'losses':len(losses),'win_rate_percent':len(wins)/len(pnl)*100 if pnl else 0.0,'net_pnl':sum(pnl),'profit_factor':pf,'expectancy_per_trade':sum(pnl)/len(pnl) if pnl else 0.0,'max_drawdown':maxdd,'positive_years':len({t['date'][:4] for t in trades if t['pnl']>0})}
