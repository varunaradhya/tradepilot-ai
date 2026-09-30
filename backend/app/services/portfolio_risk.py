from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class PortfolioRiskConfig:
    max_total_exposure_fraction: float=0.60
    max_total_risk_fraction: float=0.02
    max_sector_exposure_fraction: float=0.30
    max_single_symbol_fraction: float=0.20
    max_positions: int=10
    max_drawdown_fraction: float=0.10

@dataclass(frozen=True)
class PortfolioPosition:
    symbol: str
    market_value: float
    stop_loss_value: float
    sector: str|None=None
    correlation_group: str|None=None

@dataclass(frozen=True)
class PortfolioRiskDecision:
    allowed: bool
    reason: str
    total_exposure_fraction: float
    total_risk_fraction: float
    sector_exposure_fraction: float
    position_count: int=0

def evaluate_new_position(*,capital: float,proposed_market_value: float,proposed_risk_value: float,proposed_sector: str|None,existing_positions: Iterable[PortfolioPosition],config: PortfolioRiskConfig=PortfolioRiskConfig(),current_drawdown_fraction: float=0.0)->PortfolioRiskDecision:
    if capital <= 0 or proposed_market_value <= 0 or proposed_risk_value < 0 or current_drawdown_fraction < 0:
        return PortfolioRiskDecision(False, "INVALID_PORTFOLIO_INPUT", 0, 0, 0, 0)
    if not (
        0 < config.max_total_exposure_fraction <= 1
        and 0 < config.max_total_risk_fraction <= 1
        and 0 < config.max_sector_exposure_fraction <= 1
        and 0 < config.max_single_symbol_fraction <= 1
        and config.max_positions >= 1
        and 0 <= config.max_drawdown_fraction <= 1
    ):
        return PortfolioRiskDecision(False, "INVALID_PORTFOLIO_CONFIG", 0, 0, 0, 0)
    positions = list(existing_positions)
    if any(
        not p.symbol.strip()
        or p.market_value <= 0
        or p.stop_loss_value < 0
        for p in positions
    ):
        return PortfolioRiskDecision(False, "INVALID_EXISTING_POSITION", 0, 0, 0, len(positions))
    count = len(positions)
    total_value = sum(p.market_value for p in positions) + proposed_market_value
    total_risk = sum(p.stop_loss_value for p in positions) + proposed_risk_value
    exposure=total_value/capital; risk=total_risk/capital
    if count>=config.max_positions: return PortfolioRiskDecision(False,"MAX_POSITIONS_LIMIT",exposure,risk,0,count)
    if current_drawdown_fraction>=config.max_drawdown_fraction: return PortfolioRiskDecision(False,"PORTFOLIO_DRAWDOWN_LIMIT",exposure,risk,0,count)
    if proposed_market_value/capital>config.max_single_symbol_fraction: return PortfolioRiskDecision(False,"SINGLE_SYMBOL_EXPOSURE_LIMIT",exposure,risk,0,count)
    if exposure>config.max_total_exposure_fraction: return PortfolioRiskDecision(False,"TOTAL_EXPOSURE_LIMIT",exposure,risk,0,count)
    if risk>config.max_total_risk_fraction: return PortfolioRiskDecision(False,"TOTAL_RISK_LIMIT",exposure,risk,0,count)
    sector_fraction=0.0
    if proposed_sector:
        sector=proposed_sector.strip().upper()
        sector_value=proposed_market_value+sum(max(0,p.market_value) for p in positions if p.sector and p.sector.strip().upper()==sector)
        sector_fraction=sector_value/capital
        if sector_fraction>config.max_sector_exposure_fraction: return PortfolioRiskDecision(False,"SECTOR_EXPOSURE_LIMIT",exposure,risk,sector_fraction,count)
    return PortfolioRiskDecision(True,"APPROVED",exposure,risk,sector_fraction,count)
