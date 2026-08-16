from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence
from .fno_strategy_v1 import _ema, _rsi, _atr, FNOORBConfig

@dataclass(frozen=True)
class OptionSignal:
    action: str
    entry_time: str | None
    option_type: str | None
    reason: tuple[str, ...]

def _minute(ts) -> str:
    if isinstance(ts, (int,float)):
        return datetime.fromtimestamp(ts).strftime('%H:%M')
    s=str(ts)
    return s[11:16] if len(s)>=16 else s[-5:]

def generate_option_signal(spot_bars: Sequence[dict], option_bars: Sequence[dict], config: FNOORBConfig=FNOORBConfig()) -> OptionSignal:
    """V1 option wrapper: NIFTY 5m ORB + EMA/RSI, with option-volume confirmation."""
    need=max(config.ema_slow,config.rsi_period+1,config.atr_period+1)+3
    if len(spot_bars)<need or len(option_bars)<21:
        return OptionSignal('NO_TRADE',None,None,('INSUFFICIENT_DATA',))
    closes=[float(x['close']) for x in spot_bars]; highs=[float(x['high']) for x in spot_bars]; lows=[float(x['low']) for x in spot_bars]
    ef=_ema(closes,config.ema_fast); es=_ema(closes,config.ema_slow); r=_rsi(closes,config.rsi_period); a=_atr(highs,lows,closes,config.atr_period)
    if None in (ef,es,r,a) or a<=0: return OptionSignal('NO_TRADE',None,None,('INDICATORS_UNAVAILABLE',))
    or_high=max(float(x['high']) for x in spot_bars[:3]); or_low=min(float(x['low']) for x in spot_bars[:3]); price=closes[-1]
    vols=[float(x.get('volume',0)) for x in option_bars]; avg=sum(vols[-21:-1])/20
    if avg<=0 or vols[-1]<avg*config.volume_multiplier: return OptionSignal('NO_TRADE',None,None,('OPTION_VOLUME_CONFIRMATION_FAILED',))
    if option_bars[-1].get('strike') is None: return OptionSignal('NO_TRADE',None,None,('MISSING_STRIKE',))
    if price>or_high and price>ef>es and config.rsi_long_min<=r<=config.rsi_long_max:
        return OptionSignal('BUY',_minute(spot_bars[-1].get('timestamp')),'CE',('OPENING_RANGE_BREAKOUT','EMA_TREND','RSI_CONFIRMATION','OPTION_VOLUME_CONFIRMATION'))
    if price<or_low and price<ef<es and config.rsi_short_min<=r<=config.rsi_short_max:
        return OptionSignal('BUY',_minute(spot_bars[-1].get('timestamp')),'PE',('OPENING_RANGE_BREAKOUT','EMA_TREND','RSI_CONFIRMATION','OPTION_VOLUME_CONFIRMATION'))
    return OptionSignal('NO_TRADE',None,None,('FILTERS_NOT_ALIGNED',))

def option_position_size(capital: float,premium: float,stop_premium: float,lot_size: int,config: FNOORBConfig=FNOORBConfig()) -> int:
    if capital<=0 or premium<=0 or stop_premium<=0 or lot_size<=0:return 0
    risk_unit=abs(premium-stop_premium)
    lots=int((capital*config.risk_per_trade)//(risk_unit*lot_size)) if risk_unit>0 else 0
    return max(0,lots*lot_size)
