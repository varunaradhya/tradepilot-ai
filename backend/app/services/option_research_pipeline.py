from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from .fno_strategy_v1 import FNOORBConfig, _atr, _ema, _rsi

@dataclass(frozen=True)
class OptionResearchConfig:
    capital: float=100000.0; lot_size:int=65; expiry_flag:str='WEEK'; expiry_code:int=0; strike:str='ATM'; interval:str='5'; sl_atr:float=1.0; target_atr:float=2.0; slippage_bps:float=5.0; round_trip_cost_bps:float=12.0

def historical_nifty_lot_size(day:str)->int:
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

def _time(ts)->str:
    if isinstance(ts,(int,float)): return datetime.fromtimestamp(ts).strftime('%H:%M')
    s=str(ts); return s[11:16] if len(s)>=16 else s[-5:]

def _direction_signal(context:list[dict], day_bars:list[dict], option_history:list[dict], config:FNOORBConfig):
    """Evaluate V1 using prior bars only for indicators and today's first 3 bars for ORB."""
    if len(day_bars)<4: return None
    need=max(config.ema_slow,config.rsi_period+1,config.atr_period+1)+2
    if len(context)<need: return None
    closes=[float(x['close']) for x in context]; highs=[float(x['high']) for x in context]; lows=[float(x['low']) for x in context]
    ef=_ema(closes,config.ema_fast); es=_ema(closes,config.ema_slow); r=_rsi(closes,config.rsi_period); a=_atr(highs,lows,closes,config.atr_period)
    if None in (ef,es,r,a) or a<=0: return None
    or_high=max(float(x['high']) for x in day_bars[:3]); or_low=min(float(x['low']) for x in day_bars[:3])
    price=closes[-1]; ts=context[-1]['timestamp']
    if _time(ts)<'09:30': return None
    if price>or_high and price>ef>es and config.rsi_long_min<=r<=config.rsi_long_max: side='ce'
    elif price<or_low and price<ef<es and config.rsi_short_min<=r<=config.rsi_short_max: side='pe'
    else: return None
    current=[x for x in option_history if x['timestamp']<=ts]
    if not current: return None
    vols=[float(x.get('volume') or 0) for x in current[-21:]]
    if len(vols)<21 or sum(vols[:-1])/20<=0 or vols[-1]<sum(vols[:-1])/20*config.volume_multiplier: return None
    row=current[-1]
    if row.get('strike') is None or float(row.get('close') or 0)<=0: return None
    return side,row

def simulate_option_days(spot_rows:list[dict],option_rows:list[dict],config:OptionResearchConfig=OptionResearchConfig(),strategy_config:FNOORBConfig=FNOORBConfig())->list[dict]:
    spots=group_by_day(spot_rows); opts=group_by_day(option_rows); all_spots=sorted(spot_rows,key=lambda x:x['timestamp']); all_opts=sorted(option_rows,key=lambda x:x['timestamp']); trades=[]
    for day,sb in sorted(spots.items()):
        if day not in opts or len(sb)<4: continue
        first_ts=sb[0]['timestamp']; prior=[x for x in all_spots if x['timestamp']<first_ts]
        context=prior[-80:]
        day_opts=opts[day]
        chosen=None
        for i in range(3,len(sb)):
            current_context=context+sb[:i+1]
            ts=sb[i]['timestamp']
            for side in ('ce','pe'):
                side_history=[x for x in all_opts if x['side']==side and x['timestamp']<=ts]
                signal=_direction_signal(current_context,sb,side_history,strategy_config)
                if signal and signal[0]==side:
                    chosen=signal; break
            if chosen: break
        if not chosen: continue
        side,entry=chosen; strike=entry.get('strike'); premium=float(entry['close'])
        if premium<=0 or strike is None: continue
        future=[x for x in day_opts if x['side']==side and x.get('strike')==strike and x['timestamp']>entry['timestamp']]
        hist=[x for x in all_opts if x['side']==side and x.get('strike')==strike and x['timestamp']<=entry['timestamp']]
        if len(hist)<15 or not future: continue
        a=_atr([float(x['high']) for x in hist],[float(x['low']) for x in hist],[float(x['close']) for x in hist],14)
        if not a or a<=0: continue
        stop=max(0.05,premium-a*config.sl_atr); target=premium+a*config.target_atr; lot=historical_nifty_lot_size(day)
        risk_per_unit=max(premium-stop,0.01); lots=int((config.capital*strategy_config.risk_per_trade)//(risk_per_unit*lot)); qty=max(0,lots*lot)
        if qty<=0: continue
        exit_row=future[-1]; reason='EOD'
        for bar in future:
            if float(bar['low'])<=stop: exit_row=bar; reason='STOP'; break
            if float(bar['high'])>=target: exit_row=bar; reason='TARGET'; break
        exit_price=float(exit_row['close']); gross=(exit_price-premium)*qty; turnover=(premium+exit_price)*qty; costs=turnover*(config.round_trip_cost_bps/10000); slip=turnover*(config.slippage_bps/10000); net=gross-costs-slip
        trades.append({'date':day,'option_type':'CE' if side=='ce' else 'PE','strike':strike,'lot_size':lot,'entry':premium,'exit':exit_price,'quantity':qty,'gross_pnl':gross,'costs':costs,'slippage':slip,'pnl':net,'exit_reason':reason,'entry_timestamp':entry['timestamp'],'exit_timestamp':exit_row['timestamp'],'contract_lock':'rolling_strike_proxy','signal_reasons':['OPENING_RANGE_BREAKOUT','EMA_TREND','RSI_CONFIRMATION','OPTION_VOLUME_CONFIRMATION']})
    return trades

def summarize(trades:list[dict])->dict:
    pnl=[float(t['pnl']) for t in trades]; wins=[x for x in pnl if x>0]; losses=[x for x in pnl if x<0]; equity=peak=maxdd=0.0
    for x in pnl: equity+=x; peak=max(peak,equity); maxdd=max(maxdd,peak-equity)
    gross_win=sum(wins); gross_loss=abs(sum(losses)); pf=gross_win/gross_loss if gross_loss else None
    yearly={}
    for t in trades: yearly[t['date'][:4]]=yearly.get(t['date'][:4],0.0)+float(t['pnl'])
    return {'trades':len(pnl),'wins':len(wins),'losses':len(losses),'win_rate_percent':len(wins)/len(pnl)*100 if pnl else 0.0,'net_pnl':sum(pnl),'profit_factor':pf,'expectancy_per_trade':sum(pnl)/len(pnl) if pnl else 0.0,'max_drawdown':maxdd,'positive_years':sum(1 for v in yearly.values() if v>0)}
