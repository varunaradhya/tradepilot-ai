from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Iterable

@dataclass(frozen=True)
class CorporateActionFactor:
    symbol: str
    action_date: date
    action_type: str
    factor: float
    source: str

def validate_action(action: CorporateActionFactor) -> None:
    if not action.symbol.strip() or action.factor <= 0:
        raise ValueError("Corporate action symbol and positive factor are required")
    if action.action_type.upper() not in {"SPLIT","BONUS","RIGHTS","ADJUSTMENT"}:
        raise ValueError("Unsupported corporate action type")

def cumulative_adjustment_factor(actions: Iterable[CorporateActionFactor], as_of: date | None = None) -> dict[str,float]:
    factors: dict[str,float] = {}
    for action in actions:
        validate_action(action)
        if as_of is not None and action.action_date > as_of:
            continue
        symbol=action.symbol.strip().upper()
        factors[symbol]=factors.get(symbol,1.0)*float(action.factor)
    return factors

def adjust_ohlcv(row: dict, factor: float) -> dict:
    if factor <= 0:
        raise ValueError("Adjustment factor must be positive")
    adjusted=dict(row)
    for key in ("open","high","low","close"):
        if key in adjusted and adjusted[key] is not None:
            adjusted[key]=float(adjusted[key])*factor
    # Shares/volume scale inversely when the factor represents a price split.
    if adjusted.get("volume") is not None:
        adjusted["volume"]=float(adjusted["volume"])/factor
    adjusted["corporate_action_factor"]=factor
    return adjusted
