from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import Any

@dataclass(frozen=True)
class FNOConfig:
    min_volume: int = 1000
    min_oi: int = 10000
    max_spread_percent: float = 1.5
    min_delta: float = 0.35
    max_delta: float = 0.70
    max_iv: float = 80.0
    min_score: float = 60.0
    risk_per_trade: float = 0.005
    max_capital_percent: float = 0.20

def _num(value: Any, default: float = 0.0) -> float:
    try:
        x = float(value)
        return x if isfinite(x) else default
    except (TypeError, ValueError):
        return default

def _score(contract: dict[str, Any], cfg: FNOConfig) -> tuple[float, dict[str, float]]:
    ltp = _num(contract.get("last_price")); bid = _num(contract.get("top_bid_price")); ask = _num(contract.get("top_ask_price"))
    volume = _num(contract.get("volume")); oi = _num(contract.get("oi")); iv = _num(contract.get("implied_volatility"))
    delta = abs(_num((contract.get("greeks") or {}).get("delta")))
    spread = ((ask-bid)/((ask+bid)/2)*100) if bid > 0 and ask >= bid else 999.0
    liquidity = min(25.0, 25.0 * min(volume/max(cfg.min_volume,1), 1.0))
    oi_score = min(20.0, 20.0 * min(oi/max(cfg.min_oi,1), 1.0))
    delta_score = 20.0 if cfg.min_delta <= delta <= cfg.max_delta else max(0.0, 20.0-abs(delta-.52)*55)
    spread_score = max(0.0, 20.0-spread*12.0) if spread < cfg.max_spread_percent else 0.0
    iv_score = 15.0 if 0 < iv <= cfg.max_iv else 5.0
    price_score = 5.0 if ltp > 0 else 0.0
    return round(liquidity+oi_score+delta_score+spread_score+iv_score+price_score,2), {"liquidity":round(liquidity,2),"oi":round(oi_score,2),"delta":round(delta_score,2),"spread":round(spread_score,2),"iv":round(iv_score,2),"spread_percent":round(spread,3)}

def select_option_contracts(option_chain: dict[str, Any], direction: str, cfg: FNOConfig = FNOConfig(), limit: int = 5) -> list[dict[str, Any]]:
    direction = direction.upper()
    if direction not in {"BULLISH", "BEARISH"}: raise ValueError("direction must be BULLISH or BEARISH")
    side = "ce" if direction == "BULLISH" else "pe"
    rows=[]
    for strike_text, data in (option_chain.get("oc") or {}).items():
        try: strike=float(strike_text)
        except ValueError: continue
        contract=(data or {}).get(side)
        if not isinstance(contract,dict): continue
        score, components=_score(contract,cfg)
        if score < cfg.min_score: continue
        g=contract.get("greeks") or {}
        rows.append({"strike":strike,"option_type":"CE" if side=="ce" else "PE","security_id":contract.get("security_id"),"last_price":_num(contract.get("last_price")),"bid":_num(contract.get("top_bid_price")),"ask":_num(contract.get("top_ask_price")),"volume":int(_num(contract.get("volume"))),"oi":int(_num(contract.get("oi"))),"iv":_num(contract.get("implied_volatility")),"delta":_num(g.get("delta")),"gamma":_num(g.get("gamma")),"theta":_num(g.get("theta")),"vega":_num(g.get("vega")),"score":score,"score_components":components})
    rows.sort(key=lambda r:r["score"],reverse=True)
    return rows[:max(1,min(limit,20))]

def build_fno_decision(underlying: dict[str, Any], direction: str, candidates: list[dict[str, Any]], cfg: FNOConfig = FNOConfig()) -> dict[str, Any]:
    if not candidates: return {"decision":"NO_TRADE","reason":"NO_CONTRACT_PASSED_FILTERS","underlying":underlying}
    best=candidates[0]; premium=best["ask"] or best["last_price"]
    if premium<=0: return {"decision":"NO_TRADE","reason":"INVALID_PREMIUM","underlying":underlying}
    capital=_num(underlying.get("capital")); risk_budget=capital*cfg.risk_per_trade; max_capital=capital*cfg.max_capital_percent
    stop_pct=.25; risk_per_unit=premium*stop_pct; lot=max(1,int(_num(underlying.get("lot_size"),1)))
    qty=(int(risk_budget//risk_per_unit)//lot)*lot if risk_per_unit>0 else 0
    if premium*qty>max_capital: qty=(int(max_capital//premium)//lot)*lot
    lots=qty//lot
    if qty<=0: return {"decision":"NO_TRADE","reason":"RISK_BUDGET_TOO_SMALL_FOR_ONE_LOT","underlying":underlying,"contract":best}
    return {"decision":"QUALIFIED","direction":direction.upper(),"underlying":underlying,"contract":best,"entry":premium,"stop":round(premium*(1-stop_pct),4),"target":round(premium*1.5,4),"quantity":qty,"lots":lots,"risk_budget":round(risk_budget,2),"max_capital":round(max_capital,2),"risk_reward":2.0,"execution_mode":"PAPER_ONLY"}
