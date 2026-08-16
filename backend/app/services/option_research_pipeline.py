from __future__ import annotations
from bisect import bisect_right
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

def _series_value(d:dict, keys:tuple[str,...], i:int, default=None):
    for key in keys:
        v=d.get(key)
        if isinstance(v,list) and i < len(v): return v[i]
    return default

def _array_value(d:dict, key:str, i:int, default=None):
    v=d.get(key)
    return v[i] if isinstance(v,list) and i < len(v) else default

def normalize_rolling(payload:dict)->list[dict]:
    """Normalize Dhan rolling-option arrays. Dhan does not expose exact expiry/contract identity here."""
    data=payload.get('data',payload) if isinstance(payload,dict) else {}; rows=[]
    for side in ('ce','pe'):
        d=data.get(side) if isinstance(data,dict) else None
        if not isinstance(d,dict): continue
        required=('timestamp','open','high','low','close')
        n=max((len(d.get(k,[])) for k in required if isinstance(d.get(k,[]),list)),default=0)
        for i in range(n):
            if any(_array_value(d,k,i) is None for k in required): continue
            expiry=_series_value(d,('expiry','expiry_date','expiration','expiration_date'),i)
            contract=_series_value(d,('contract','contract_symbol','option_symbol','instrument_token'),i)
            rows.append({'side':side,'timestamp':d['timestamp'][i],'open':d['open'][i],'high':d['high'][i],'low':d['low'][i],'close':d['close'][i],'volume':_array_value(d,'volume',i,0),'strike':_array_value(d,'strike',i),'oi':_array_value(d,'oi',i),'iv':_array_value(d,'iv',i),'spot':_array_value(d,'spot',i),'expiry':expiry,'contract_identity':str(contract) if contract is not None else None})
    return rows

def normalize_spot(payload:dict)->list[dict]:
    data=payload.get('data',payload) if isinstance(payload,dict) else {}
    if not isinstance(data,dict): return []
    n=max((len(data.get(k,[])) for k in ('timestamp','open','high','low','close') if isinstance(data.get(k,[]),list)),default=0)
    return [{'timestamp':data['timestamp'][i],'open':data['open'][i],'high':data['high'][i],'low':data['low'][i],'close':data['close'][i],'volume':_array_value(data,'volume',i,0)} for i in range(n) if all(_array_value(data,k,i) is not None for k in ('timestamp','open','high','low','close'))]

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
    if len(day_bars)<4: return None
    need=max(config.ema_slow,config.rsi_period+1,config.atr_period+1)+2
    if len(context)<need: return None
    closes=[float(x['close']) for x in context]; highs=[float(x['high']) for x in context]; lows=[float(x['low']) for x in context]
    ef=_ema(closes,config.ema_fast); es=_ema(closes,config.ema_slow); r=_rsi(closes,config.rsi_period); a=_atr(highs,lows,closes,config.atr_period)
    if None in (ef,es,r,a) or a<=0: return None
    or_high=max(float(x['high']) for x in day_bars[:3]); or_low=min(float(x['low']) for x in day_bars[:3]); price=closes[-1]; ts=context[-1]['timestamp']
    if _time(ts)<'09:30': return None
    if price>or_high and price>ef>es and config.rsi_long_min<=r<=config.rsi_long_max: side='ce'
    elif price<or_low and price<ef<es and config.rsi_short_min<=r<=config.rsi_short_max: side='pe'
    else: return None
    if len(option_history)<21: return None
    vols=[float(x.get('volume') or 0) for x in option_history[-21:]]
    if sum(vols[:-1])/20<=0 or vols[-1]<sum(vols[:-1])/20*config.volume_multiplier: return None
    row=option_history[-1]
    if row.get('strike') is None or float(row.get('close') or 0)<=0: return None
    return side,row

def _prepare_option_index(option_rows:list[dict]):
    all_opts=sorted(option_rows,key=lambda x:x['timestamp']); by_side={side:[] for side in ('ce','pe')}
    for row in all_opts:
        if row.get('side') in by_side: by_side[row['side']].append(row)
    return {side:{'rows':rows,'timestamps':[r['timestamp'] for r in rows]} for side,rows in by_side.items()}

def _history_until(index,ts):
    rows=index['rows']; return rows[:bisect_right(index['timestamps'],ts)]

def _future_for_contract(day_opts,side,strike,entry_ts,contract_identity=None,expiry=None):
    return [x for x in day_opts if x['side']==side and x.get('strike')==strike and x['timestamp']>entry_ts and (contract_identity is None or x.get('contract_identity')==contract_identity) and (expiry is None or x.get('expiry')==expiry)]

def _history_for_contract(index,side,strike,entry_ts,contract_identity=None,expiry=None):
    rows=index[side]['rows']; pos=bisect_right(index[side]['timestamps'],entry_ts)
    return [x for x in rows[:pos] if x.get('strike')==strike and (contract_identity is None or x.get('contract_identity')==contract_identity) and (expiry is None or x.get('expiry')==expiry)]

def simulate_option_days(spot_rows:list[dict],option_rows:list[dict],config:OptionResearchConfig=OptionResearchConfig(),strategy_config:FNOORBConfig=FNOORBConfig())->list[dict]:
    spots=group_by_day(spot_rows); opts=group_by_day(option_rows); all_spots=sorted(spot_rows,key=lambda x:x['timestamp']); opt_index=_prepare_option_index(option_rows); trades=[]
    print(f'Backtest engine: {len(spots)} sessions, {len(option_rows)} option rows')
    for day_no,(day,sb) in enumerate(sorted(spots.items()),1):
        if day not in opts or len(sb)<4: continue
        first_ts=sb[0]['timestamp']; prior=[x for x in all_spots if x['timestamp']<first_ts]; context=prior[-80:]; day_opts=opts[day]; chosen=None
        for i in range(3,len(sb)):
            current_context=context+sb[:i+1]; ts=sb[i]['timestamp']
            for side in ('ce','pe'):
                history=_history_until(opt_index[side],ts); signal=_direction_signal(current_context,sb,history,strategy_config)
                if signal and signal[0]==side: chosen=signal; break
            if chosen: break
        if not chosen: continue
        side,entry=chosen; strike=entry.get('strike'); premium=float(entry['close']); contract_identity=entry.get('contract_identity'); expiry=entry.get('expiry')
        if premium<=0 or strike is None or not contract_identity or not expiry: continue
        future=_future_for_contract(day_opts,side,strike,entry['timestamp'],contract_identity,expiry); hist=_history_for_contract(opt_index,side,strike,entry['timestamp'],contract_identity,expiry)
        if len(hist)<15 or not future: continue
        a=_atr([float(x['high']) for x in hist],[float(x['low']) for x in hist],[float(x['close']) for x in hist],14)
        if not a or a<=0: continue
        stop=max(0.05,premium-a*config.sl_atr); target=premium+a*config.target_atr; lot=historical_nifty_lot_size(day); risk_per_unit=max(premium-stop,0.01); lots=int((config.capital*strategy_config.risk_per_trade)//(risk_per_unit*lot)); qty=max(0,lots*lot)
        if qty<=0: continue
        exit_row=future[-1]; reason='EOD'
        for bar in future:
            if float(bar['low'])<=stop: exit_row=bar; reason='STOP'; break
            if float(bar['high'])>=target: exit_row=bar; reason='TARGET'; break
        exit_price=float(exit_row['close']); gross=(exit_price-premium)*qty; turnover=(premium+exit_price)*qty; costs=turnover*(config.round_trip_cost_bps/10000); slip=turnover*(config.slippage_bps/10000); net=gross-costs-slip
        lock_mode='rolling_series_identity' if str(contract_identity).startswith('ROLLING:') else 'exact_contract_identity'
        trades.append({'date':day,'option_type':'CE' if side=='ce' else 'PE','strike':strike,'expiry':expiry,'contract_identity':contract_identity,'lot_size':lot,'entry':premium,'exit':exit_price,'quantity':qty,'gross_pnl':gross,'costs':costs,'slippage':slip,'pnl':net,'exit_reason':reason,'entry_timestamp':entry['timestamp'],'exit_timestamp':exit_row['timestamp'],'contract_lock':lock_mode,'signal_reasons':['OPENING_RANGE_BREAKOUT','EMA_TREND','RSI_CONFIRMATION','OPTION_VOLUME_CONFIRMATION']})
        if day_no%100==0: print(f'  processed {day_no}/{len(spots)} sessions; trades={len(trades)}')
    return trades

def summarize(trades:list[dict])->dict:
    pnl=[float(t['pnl']) for t in trades]; wins=[x for x in pnl if x>0]; losses=[x for x in pnl if x<0]; equity=peak=maxdd=0.0
    for x in pnl: equity+=x; peak=max(peak,equity); maxdd=max(maxdd,peak-equity)
    gross_win=sum(wins); gross_loss=abs(sum(losses)); pf=gross_win/gross_loss if gross_loss else None; yearly={}
    for t in trades: yearly[t['date'][:4]]=yearly.get(t['date'][:4],0.0)+float(t['pnl'])
    return {'trades':len(pnl),'wins':len(wins),'losses':len(losses),'win_rate_percent':len(wins)/len(pnl)*100 if pnl else 0.0,'net_pnl':sum(pnl),'profit_factor':pf,'expectancy_per_trade':sum(pnl)/len(pnl) if pnl else 0.0,'max_drawdown':maxdd,'positive_years':sum(1 for v in yearly.values() if v>0)}
