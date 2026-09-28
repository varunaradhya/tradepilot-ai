from __future__ import annotations
from dataclasses import asdict, is_dataclass
from typing import Any, Callable
from app.services.intraday_strategy import IntradayConfig, generate_intraday_signal
from app.services.intraday_strategy_v2 import (
    IntradayV2AConfig,
    IntradayV2Config,
    generate_intraday_v2_signal,
    generate_intraday_v2a_signal,
)

class StrategyDefinition:
    def __init__(self,version:str,name:str,config_factory:Callable[[],Any],signal_fn:Callable[...,Any]):
        self.version=version; self.name=name; self.config_factory=config_factory; self.signal_fn=signal_fn
    def metadata(self)->dict:
        config=self.config_factory()
        return {"version":self.version,"name":self.name,"config":asdict(config) if is_dataclass(config) else {},"execution_mode":"SIMULATION_ONLY"}

STRATEGIES={
    "V1":StrategyDefinition("V1","Opening Range Breakout",IntradayConfig,generate_intraday_signal),
    "V2":StrategyDefinition("V2","Enhanced Intraday Research",IntradayV2Config,generate_intraday_v2_signal),
    "V2A":StrategyDefinition("V2A","Enhanced ORB - Breakout Quality",IntradayV2AConfig,generate_intraday_v2a_signal),
}
def list_strategies()->list[dict]:
    return [STRATEGIES[key].metadata() for key in sorted(STRATEGIES)]
def get_strategy(version:str)->StrategyDefinition:
    key=version.strip().upper()
    if key not in STRATEGIES: raise ValueError(f"Unsupported strategy version: {key}")
    return STRATEGIES[key]
