from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, date, time
from zoneinfo import ZoneInfo

IST=ZoneInfo("Asia/Kolkata")

@dataclass(frozen=True)
class MarketSchedulerConfig:
    market_open: time=time(9,15)
    market_close: time=time(15,30)
    timezone_name: str="Asia/Kolkata"
    holidays: frozenset[date]=frozenset()

def scheduler_status(now: datetime|None=None, config: MarketSchedulerConfig=MarketSchedulerConfig())->dict:
    tz=ZoneInfo(config.timezone_name)
    current=(now or datetime.now(tz)).astimezone(tz)
    d=current.date(); local_time=current.time().replace(tzinfo=None)
    holiday=d in config.holidays
    weekday=current.weekday()<5
    in_session=weekday and not holiday and config.market_open<=local_time<=config.market_close
    return {"timezone":config.timezone_name,"timestamp":current.isoformat(),"market":"NSE_EQ","date":d.isoformat(),"weekday":weekday,"holiday":holiday,"market_open":config.market_open.isoformat(),"market_close":config.market_close.isoformat(),"session_active":in_session,"mode":"SIMULATION_ONLY","broker_orders_enabled":False}

def is_trading_day(day:date, holidays:frozenset[date]=frozenset())->bool:
    return day.weekday()<5 and day not in holidays
