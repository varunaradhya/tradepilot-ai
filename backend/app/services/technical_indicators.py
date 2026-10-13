"""Deterministic, look-ahead-safe technical indicators."""
from __future__ import annotations
from math import isfinite, sqrt
from typing import Iterable

Number = float | int | None

def _clean(values: Iterable[Number]) -> list[float | None]:
    out=[]
    for value in values:
        if value is None: out.append(None)
        else:
            x=float(value); out.append(x if isfinite(x) else None)
    return out

def sma(values: Iterable[Number], period: int) -> list[float | None]:
    if period <= 0: raise ValueError("period must be positive")
    values=_clean(values); result=[None]*len(values); window=[]
    for i,value in enumerate(values):
        if value is None: window=[]; continue
        window.append(value)
        if len(window)>period: window.pop(0)
        if len(window)==period: result[i]=sum(window)/period
    return result

def ema(values: Iterable[Number], period: int) -> list[float | None]:
    if period <= 0: raise ValueError("period must be positive")
    values=_clean(values); result=[None]*len(values); alpha=2/(period+1); window=[]; previous=None
    for i,value in enumerate(values):
        if value is None: window=[]; previous=None; continue
        if previous is None:
            window.append(value)
            if len(window)<period: continue
            previous=sum(window)/period
        else: previous=alpha*value+(1-alpha)*previous
        result[i]=previous
    return result

def rsi(values: Iterable[Number], period: int=14) -> list[float | None]:
    if period<=0: raise ValueError("period must be positive")
    values=_clean(values); result=[None]*len(values); gains=[]; losses=[]; previous=None; avg_gain=None; avg_loss=None
    for i,value in enumerate(values):
        if value is None or previous is None:
            previous=value; gains=[]; losses=[]; avg_gain=avg_loss=None; continue
        change=value-previous; gain=max(change,0.0); loss=max(-change,0.0)
        if avg_gain is None:
            gains.append(gain); losses.append(loss)
            if len(gains)==period: avg_gain=sum(gains)/period; avg_loss=sum(losses)/period
        else:
            avg_gain=((avg_gain*(period-1))+gain)/period
            avg_loss=((avg_loss*(period-1))+loss)/period
        if avg_gain is not None and avg_loss is not None:
            result[i]=100.0 if avg_loss==0 and avg_gain>0 else 50.0 if avg_loss==0 else 100-(100/(1+avg_gain/avg_loss))
        previous=value
    return result

def bollinger(values: Iterable[Number], period:int=20, deviations:float=2.0):
    if period<=0 or deviations<0: raise ValueError("invalid Bollinger parameters")
    values=_clean(values); middle=sma(values,period); upper=[None]*len(values); lower=[None]*len(values); window=[]
    for i,value in enumerate(values):
        if value is None: window=[]; continue
        window.append(value)
        if len(window)>period: window.pop(0)
        if len(window)==period:
            mean=sum(window)/period; sd=sqrt(sum((x-mean)**2 for x in window)/period)
            upper[i]=mean+deviations*sd; lower[i]=mean-deviations*sd
    return middle,upper,lower

def macd(values: Iterable[Number], fast_period:int=12, slow_period:int=26, signal_period:int=9):
    fast=ema(values,fast_period); slow=ema(values,slow_period)
    line=[None if a is None or b is None else a-b for a,b in zip(fast,slow)]
    signal=ema(line,signal_period); histogram=[None if a is None or b is None else a-b for a,b in zip(line,signal)]
    return line,signal,histogram

def true_range(high,low,close):
    highs,lows,closes=_clean(high),_clean(low),_clean(close); result=[None]*len(highs); previous=None
    for i,(h,l,c) in enumerate(zip(highs,lows,closes)):
        if h is None or l is None: previous=c; continue
        result[i]=max(h-l,abs(h-previous),abs(l-previous)) if previous is not None else h-l
        previous=c
    return result

def atr(high,low,close,period:int=14): return sma(true_range(high,low,close),period)

def vwap(high,low,close,volume,timestamps=None):
    highs,lows,closes,volumes=map(_clean,(high,low,close,volume)); result=[None]*len(closes); pv=0.0; vv=0.0; session=None
    times=list(timestamps) if timestamps is not None else [None]*len(closes)
    for i,(h,l,c,v,stamp) in enumerate(zip(highs,lows,closes,volumes,times)):
        current_session=stamp.date() if hasattr(stamp,"date") else str(stamp)[:10] if stamp is not None else None
        if current_session is not None and session is not None and current_session!=session: pv=0.0; vv=0.0
        if current_session is not None: session=current_session
        if h is None or l is None or c is None or v is None or v<=0: continue
        pv+=((h+l+c)/3)*v; vv+=v; result[i]=pv/vv if vv else None
    return result

def relative_volume(volume,period:int=20):
    values=_clean(volume); result=[None]*len(values); window=[]
    for i,value in enumerate(values):
        if value is None: window=[]; continue
        if len(window)==period:
            avg=sum(window)/period; result[i]=value/avg if avg>0 else None
        window.append(value)
        if len(window)>period: window.pop(0)
    return result

def calculate_indicators(bars:list[dict]):
    closes=[b.get("close") for b in bars]; highs=[b.get("high") for b in bars]; lows=[b.get("low") for b in bars]; volumes=[b.get("volume") for b in bars]
    macd_line,macd_signal,macd_hist=macd(closes)
    bb_mid,bb_upper,bb_lower=bollinger(closes)
    return {"sma20":sma(closes,20),"sma50":sma(closes,50),"sma200":sma(closes,200),"ema9":ema(closes,9),"ema21":ema(closes,21),"rsi14":rsi(closes,14),"macd":macd_line,"macd_signal":macd_signal,"macd_histogram":macd_hist,"bollinger_middle":bb_mid,"bollinger_upper":bb_upper,"bollinger_lower":bb_lower,"atr14":atr(highs,lows,closes,14),"vwap":vwap(highs,lows,closes,volumes,[b.get("timestamp") for b in bars]),"relative_volume20":relative_volume(volumes,20)}

def _last(values):
    return next((x for x in reversed(values) if x is not None),None)

def build_signal(bars,indicators):
    if not bars or bars[-1].get("close") is None: return {"direction":"neutral","conditions":[],"invalidation":[],"sufficient_data":False}
    close=bars[-1]["close"]; conditions=[]; bullish=bearish=0
    for key in ("sma20","sma50","sma200"):
        value=_last(indicators[key])
        if value is not None:
            if close>value: bullish+=1; conditions.append(f"Price is above {key.upper()}")
            elif close<value: bearish+=1; conditions.append(f"Price is below {key.upper()}")
    e9,e21=_last(indicators["ema9"]),_last(indicators["ema21"])
    if e9 is not None and e21 is not None:
        if e9>e21: bullish+=1; conditions.append("EMA 9 is above EMA 21")
        elif e9<e21: bearish+=1; conditions.append("EMA 9 is below EMA 21")
    rv=_last(indicators["rsi14"])
    if rv is not None:
        if rv<30: bullish+=1; conditions.append("RSI 14 is below 30")
        elif rv>70: bearish+=1; conditions.append("RSI 14 is above 70")
    ml,ms=_last(indicators["macd"]),_last(indicators["macd_signal"])
    if ml is not None and ms is not None:
        if ml>ms: bullish+=1; conditions.append("MACD is above its signal line")
        elif ml<ms: bearish+=1; conditions.append("MACD is below its signal line")
    sufficient=sum(1 for b in bars if b.get("close") is not None)>=35
    direction="bullish" if bullish>bearish else "bearish" if bearish>bullish else "neutral"
    if not sufficient: direction="neutral"
    return {"direction":direction,"bullish_conditions":bullish,"bearish_conditions":bearish,"conditions":conditions,"invalidation":["Signal is invalidated if the underlying trend conditions materially reverse."],"sufficient_data":sufficient}
