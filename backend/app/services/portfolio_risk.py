from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class PortfolioRiskConfig:
    max_total_exposure_fraction: float = 0.60
    max_total_risk_fraction: float = 0.02
    max_sector_exposure_fraction: float = 0.30
    max_single_symbol_fraction: float = 0.20


@dataclass(frozen=True)
class PortfolioPosition:
    symbol: str
    market_value: float
    stop_loss_value: float
    sector: str | None = None


@dataclass(frozen=True)
class PortfolioRiskDecision:
    allowed: bool
    reason: str
    total_exposure_fraction: float
    total_risk_fraction: float
    sector_exposure_fraction: float


def evaluate_new_position(
    *,
    capital: float,
    proposed_market_value: float,
    proposed_risk_value: float,
    proposed_sector: str | None,
    existing_positions: Iterable[PortfolioPosition],
    config: PortfolioRiskConfig = PortfolioRiskConfig(),
) -> PortfolioRiskDecision:
    """Fail-closed portfolio-level exposure/risk gate.

    Correlation is intentionally not guessed here. Sector concentration is a
    conservative proxy until reliable historical correlation data is available.
    """
    if capital <= 0 or proposed_market_value <= 0 or proposed_risk_value < 0:
        return PortfolioRiskDecision(False, "INVALID_PORTFOLIO_INPUT", 0.0, 0.0, 0.0)

    positions = list(existing_positions)
    total_value = sum(max(0.0, p.market_value) for p in positions) + proposed_market_value
    total_risk = sum(max(0.0, p.stop_loss_value) for p in positions) + proposed_risk_value
    exposure_fraction = total_value / capital
    risk_fraction = total_risk / capital

    if proposed_market_value / capital > config.max_single_symbol_fraction:
        return PortfolioRiskDecision(False, "SINGLE_SYMBOL_EXPOSURE_LIMIT", exposure_fraction, risk_fraction, 0.0)
    if exposure_fraction > config.max_total_exposure_fraction:
        return PortfolioRiskDecision(False, "TOTAL_EXPOSURE_LIMIT", exposure_fraction, risk_fraction, 0.0)
    if risk_fraction > config.max_total_risk_fraction:
        return PortfolioRiskDecision(False, "TOTAL_RISK_LIMIT", exposure_fraction, risk_fraction, 0.0)

    sector_fraction = 0.0
    if proposed_sector:
        sector = proposed_sector.strip().upper()
        sector_value = proposed_market_value + sum(
            max(0.0, p.market_value)
            for p in positions
            if p.sector and p.sector.strip().upper() == sector
        )
        sector_fraction = sector_value / capital
        if sector_fraction > config.max_sector_exposure_fraction:
            return PortfolioRiskDecision(False, "SECTOR_EXPOSURE_LIMIT", exposure_fraction, risk_fraction, sector_fraction)

    return PortfolioRiskDecision(True, "APPROVED", exposure_fraction, risk_fraction, sector_fraction)
