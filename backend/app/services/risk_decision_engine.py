from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from app.services.market_regime import MarketRegime, classify_market_regime
from app.services.portfolio_risk import (
    PortfolioPosition,
    PortfolioRiskConfig,
    evaluate_new_position,
)
from app.services.trade_decision_service import TradeDecision, build_paper_trade_decision


@dataclass(frozen=True)
class RiskAwareDecision:
    decision: TradeDecision
    regime: MarketRegime
    portfolio_allowed: bool
    portfolio_reason: str
    total_exposure_fraction: float
    total_risk_fraction: float
    sector_exposure_fraction: float

    def as_dict(self) -> dict:
        return {
            "decision": self.decision.as_dict(),
            "risk_context": {
                "market_regime": asdict(self.regime),
                "portfolio_allowed": self.portfolio_allowed,
                "portfolio_reason": self.portfolio_reason,
                "total_exposure_fraction": self.total_exposure_fraction,
                "total_risk_fraction": self.total_risk_fraction,
                "sector_exposure_fraction": self.sector_exposure_fraction,
            },
        }


def _blocked_decision(decision: TradeDecision, reason: str) -> TradeDecision:
    return TradeDecision(
        signal_id=decision.signal_id,
        symbol=decision.symbol,
        action=decision.action,
        status="BLOCKED",
        reason=reason,
        confidence=decision.confidence,
        entry=decision.entry,
        stop=decision.stop,
        target=decision.target,
        risk_reward=decision.risk_reward,
        quantity=0,
        capital_required=0.0,
        max_loss=0.0,
        broker=decision.broker,
        mode=decision.mode,
    )


def build_risk_aware_paper_trade_decision(
    *,
    symbol: str,
    session: str,
    closes: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    volumes: Sequence[float],
    equity: float,
    existing_positions: Sequence[PortfolioPosition] = (),
    sector: str | None = None,
    portfolio_config: PortfolioRiskConfig | None = None,
    broker: str = "DHAN",
    in_market_session: bool = True,
    market_data_healthy: bool = True,
    strategy_ready: bool = True,
    risk_approved: bool = True,
    daily_risk_used: float = 0.0,
    opening_high: float | None = None,
    min_confidence: float = 65.0,
) -> RiskAwareDecision:
    """Run paper trading through regime and portfolio risk gates.

    This is fail-closed: insufficient market history and bearish regimes are
    blocked before a trade can become paper-ready, and portfolio exposure and
    risk limits are checked before authorization. No broker order is sent.
    """
    regime = classify_market_regime(list(closes))
    base = build_paper_trade_decision(
        symbol=symbol,
        session=session,
        closes=closes,
        highs=highs,
        lows=lows,
        volumes=volumes,
        equity=equity,
        broker=broker,
        in_market_session=in_market_session,
        market_data_healthy=market_data_healthy,
        strategy_ready=strategy_ready,
        risk_approved=risk_approved,
        daily_risk_used=daily_risk_used,
        opening_high=opening_high,
        min_confidence=min_confidence,
    )

    if regime.label == "INSUFFICIENT_DATA":
        return RiskAwareDecision(
            _blocked_decision(base, "MARKET_REGIME_DATA_INSUFFICIENT"),
            regime,
            False,
            "MARKET_REGIME_DATA_INSUFFICIENT",
            0.0,
            0.0,
            0.0,
        )

    if regime.label == "BEAR":
        return RiskAwareDecision(
            _blocked_decision(base, "MARKET_REGIME_UNFAVORABLE"),
            regime,
            False,
            "MARKET_REGIME_UNFAVORABLE",
            0.0,
            0.0,
            0.0,
        )

    if base.status != "PAPER_READY":
        return RiskAwareDecision(base, regime, True, "NOT_APPLICABLE", 0.0, 0.0, 0.0)

    portfolio = evaluate_new_position(
        capital=equity,
        proposed_market_value=base.capital_required,
        proposed_risk_value=base.max_loss,
        proposed_sector=sector,
        existing_positions=existing_positions,
        config=portfolio_config or PortfolioRiskConfig(),
    )

    if not portfolio.allowed:
        return RiskAwareDecision(
            _blocked_decision(base, portfolio.reason),
            regime,
            False,
            portfolio.reason,
            portfolio.total_exposure_fraction,
            portfolio.total_risk_fraction,
            portfolio.sector_exposure_fraction,
        )

    return RiskAwareDecision(
        base,
        regime,
        True,
        portfolio.reason,
        portfolio.total_exposure_fraction,
        portfolio.total_risk_fraction,
        portfolio.sector_exposure_fraction,
    )
