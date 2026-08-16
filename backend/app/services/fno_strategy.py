from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import Any
@dataclass(frozen=True)
class FNOConfig:
 min_volume:int=1000; min_oi:int=10000; max_spread_percent:float=1.5; min_delta:float=.35; max_delta:float=.70; max_iv:float=80.; min_score:float=60.; risk_per_trade:float=.005; max_capital_percent:float=.20
def _num(v:Any,d:float=0.)->float:
 try:x=float(v);return x if isfinite(x) else d
 except(TypeError,ValueError):return d
def _score(c:dict[str,Any],cfg:FNOConfig):
 ltp=_num(c.get("last_price"));bid=_num(c.get("top_bid_price"));ask=_num(c.get("top_ask_price"));vol=_num(c.get("volume"));oi=_num(c.get("oi"));iv=_num(c.get("implied_volatility"));delta=abs(_num((c.get("greeks")or{}).get("delta")));spread=((ask-bid)/((ask+bid)/2)*100) if bid>0 and ask>=bid else 999.
 a=min(25.,25.*min(vol/max(cfg.min_volume,1),1.));b=min(20.,20.*min(oi/max(cfg.min_oi,1),1.));d=20. if cfg.min_delta<=delta<=cfg.max_delta else max(0.,20.-abs(delta-.52)*55);s=max(0.,20.-spread*12.) if spread<cfg.max_spread_percent else 0.;i=15. if 0<iv<=cfg.max_iv else 5.;p=5. if ltp>0 else 0.
 return round(a+b+d+s+i+p,2),{"liquidity":round(a,2),"oi":round(b,2),"delta":round(d,2),"spread":round(s,2),"iv":round(i,2),"spread_percent":round(spread,3)}
def select_option_contracts(chain:dict[str,Any],direction:str,cfg:FNOConfig=FNOConfig(),limit:int=5):
 direction=direction.upper()
 if direction not in {"BULLISH","BEARISH"}:raise ValueError("direction must be BULLISH or BEARISH")
 side="ce" if direction=="BULLISH" else "pe";rows=[]
 for st,data in (chain.get("oc")or{}).items():
  try:strike=float(st)
  except ValueError:continue
  c=(data or {}).get(side)
  if not isinstance(c,dict):continue
  score,comp=_score(c,cfg)
  if score<cfg.min_score:continue
  g=c.get("greeks")or{};rows.append({"strike":strike,"option_type":"CE" if side=="ce" else "PE","security_id":c.get("security_id"),"last_price":_num(c.get("last_price")),"bid":_num(c.get("top_bid_price")),"ask":_num(c.get("top_ask_price")),"volume":int(_num(c.get("volume"))),"oi":int(_num(c.get("oi"))),"iv":_num(c.get("implied_volatility")),"delta":_num(g.get("delta")),"gamma":_num(g.get("gamma")),"theta":_num(g.get("theta")),"vega":_num(g.get("vega")),"score":score,"score_components":comp})
 rows.sort(key=lambda r:r["score"],reverse=True);return rows[:max(1,min(limit,20))]
def build_fno_decision(underlying:dict[str,Any],direction:str,candidates:list[dict[str,Any]],cfg:FNOConfig=FNOConfig()):
 if not candidates:return {"decision":"NO_TRADE","reason":"NO_CONTRACT_PASSED_FILTERS","underlying":underlying}
 best=candidates[0];premium=best["ask"] or best["last_price"]
 if premium<=0:return {"decision":"NO_TRADE","reason":"INVALID_PREMIUM","underlying":underlying}
 capital=_num(underlying.get("capital"));risk_budget=capital*cfg.risk_per_trade;max_capital=capital*cfg.max_capital_percent;stop_pct=.25;risk_unit=premium*stop_pct;lot=max(1,int(_num(underlying.get("lot_size"),1)));qty=(int(risk_budget//risk_unit)//lot)*lot if risk_unit>0 else 0
 if premium*qty>max_capital:qty=(int(max_capital//premium)//lot)*lot
 lots=qty//lot
 if qty<=0:return {"decision":"NO_TRADE","reason":"RISK_BUDGET_TOO_SMALL_FOR_ONE_LOT","underlying":underlying,"contract":best,"lot_size":lot}
 return {"decision":"QUALIFIED","direction":direction.upper(),"underlying":underlying,"contract":best,"entry":premium,"stop":round(premium*(1-stop_pct),4),"target":round(premium*1.5,4),"quantity":qty,"lots":lots,"lot_size":lot,"risk_budget":round(risk_budget,2),"max_capital":round(max_capital,2),"risk_reward":2.,"execution_mode":"PAPER_ONLY"}
