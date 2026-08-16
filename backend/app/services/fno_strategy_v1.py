from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import Sequence

@dataclass(frozen=True)
class FNOORBConfig:
    """Frozen V1 strategy: 5-minute NIFTY F&O opening-range breakout."""
    opening_range_minutes: int = 15
    ema_fast: int = 20
    ema_slow: int = 50
    rsi_period: int = 14
    atr_period: int = 14
    volume_period: int = 20
    volume_multiplier: float = 1.20
    rsi_long_min: float = 55.0
    rsi_long_max: float = 70.0
    rsi_short_min: float = 30.0
    rsi_short_max: float = 45.0
    stop_atr: float = 1.0
    target_atr: float = 2.0
    risk_per_trade: float = 0.005
    max_trades_per_day: int = 1
    entry_start: str = "09:30"
    entry_cutoff: str = "14:30"
    square_off: str = "15:15"
    slippage_bps: float = 2.0
    round_trip_cost_bps: float = 12.0

@dataclass(frozen=True)
class Signal:
    action: str
    score: int
    entry: float | None
    stop: float | None
    target: float | None
    reason: tuple[str, ...]


def _ema(values: Sequence[float], period: int) -> float | None:
    if len(values) < period or period <= 0: return None
    k = 2.0 / (period + 1)
    e = float(values[0])
    for v in values[1:]: e = float(v) * k + e * (1-k)
    return e


def _rsi(values: Sequence[float], period: int) -> float | None:
    if len(values) < period + 1: return None
    gains=[]; losses=[]
    for a,b in zip(values[-period-1:-1], values[-period:]):
        d=float(b)-float(a); gains.append(max(d,0)); losses.append(max(-d,0))
    ag=sum(gains)/period; al=sum(losses)/period
    if al == 0: return 100.0
    return 100.0 - 100.0/(1.0 + ag/al)


def _atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int) -> float | None:
    if len(closes) < period+1: return None
    trs=[]
    start=len(closes)-period
    for i in range(start, len(closes)):
        trs.append(max(float(highs[i])-float(lows[i]), abs(float(highs[i])-float(closes[i-1])), abs(float(lows[i])-float(closes[i-1]))))
    return sum(trs)/period if trs else None


def _vwap(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], volumes: Sequence[float]) -> float | None:
    if not volumes or len(volumes)!=len(closes): return None
    pv=0.0; vol=0.0
    for h,l,c,v in zip(highs,lows,closes,volumes):
        pv += ((float(h)+float(l)+float(c))/3.0)*float(v); vol += float(v)
    return pv/vol if vol>0 else None


def generate_signal(bars: Sequence[dict], config: FNOORBConfig=FNOORBConfig()) -> Signal:
    if len(bars) < max(config.ema_slow, config.volume_period, config.rsi_period+1, config.atr_period+1) + 3:
        return Signal("NO_TRADE",0,None,None,None,("INSUFFICIENT_DATA",))
    try:
        closes=[float(x["close"]) for x in bars]; highs=[float(x["high"]) for x in bars]; lows=[float(x["low"]) for x in bars]; volumes=[float(x.get("volume",0)) for x in bars]
        if not all(isfinite(x) for x in closes+highs+lows+volumes): raise ValueError
    except (KeyError,ValueError,TypeError):
        return Signal("NO_TRADE",0,None,None,None,("INVALID_DATA",))
    if len(bars) < 4: return Signal("NO_TRADE",0,None,None,None,("INSUFFICIENT_SESSION",))
    # Caller supplies one session of 5-minute bars. The first three bars are 09:15-09:30.
    or_bars=bars[:3]
    or_high=max(float(x["high"]) for x in or_bars); or_low=min(float(x["low"]) for x in or_bars)
    price=closes[-1]; ef=_ema(closes,config.ema_fast); es=_ema(closes,config.ema_slow); r=_rsi(closes,config.rsi_period); a=_atr(highs,lows,closes,config.atr_period); vwap=_vwap(highs,lows,closes,volumes)
    avg_vol=sum(volumes[-config.volume_period-1:-1])/config.volume_period if len(volumes)>config.volume_period else None
    if None in (ef,es,r,a,vwap,avg_vol) or a<=0 or avg_vol<=0: return Signal("NO_TRADE",0,None,None,None,("INDICATORS_UNAVAILABLE",))
    long_ok=price>or_high and price>ef>es and price>vwap and config.rsi_long_min<=r<=config.rsi_long_max and volumes[-1]>=avg_vol*config.volume_multiplier
    short_ok=price<or_low and price<ef<es and price<vwap and config.rsi_short_min<=r<=config.rsi_short_max and volumes[-1]>=avg_vol*config.volume_multiplier
    if not long_ok and not short_ok: return Signal("NO_TRADE",0,None,None,None,("FILTERS_NOT_ALIGNED",))
    action="BUY" if long_ok else "SELL"; stop=price-a*config.stop_atr; target=price+a*config.target_atr
    if action=="SELL": stop=price+a*config.stop_atr; target=price-a*config.target_atr
    return Signal(action,100,price,stop,target,("OPENING_RANGE_BREAKOUT","EMA_TREND","VWAP_CONFIRMATION","RSI_CONFIRMATION","VOLUME_CONFIRMATION"))


def position_size(capital: float, entry: float, stop: float, lot_size: int, config: FNOORBConfig=FNOORBConfig()) -> int:
    if capital<=0 or entry<=0 or stop<=0 or lot_size<=0: return 0
    risk_budget=capital*config.risk_per_trade; risk_per_unit=abs(entry-stop)
    if risk_per_unit<=0: return 0
    lots=int(risk_budget//(risk_per_unit*lot_size))
    return max(0,lots*lot_size)
