from app.services.portfolio_risk import PortfolioPosition
from app.services.risk_decision_engine import build_risk_aware_paper_trade_decision


def _series(up=True):
    base = [100 + i for i in range(50)] if up else [150 - i for i in range(50)]
    highs = [x + 1 for x in base]
    lows = [x - 1 for x in base]
    volumes = [1000] * 49 + [1500]
    return base, highs, lows, volumes


def test_risk_engine_blocks_bear_regime():
    closes, highs, lows, volumes = _series(up=False)
    result = build_risk_aware_paper_trade_decision(
        symbol="TCS",
        session="2026-08-17",
        closes=closes,
        highs=highs,
        lows=lows,
        volumes=volumes,
        equity=100000,
    )
    assert result.regime.label == "BEAR"
    assert result.decision.status == "BLOCKED"
    assert result.decision.reason == "MARKET_REGIME_UNFAVORABLE"


def test_risk_engine_blocks_insufficient_regime_data():
    closes = [100 + i for i in range(20)]
    highs = [x + 1 for x in closes]
    lows = [x - 1 for x in closes]
    volumes = [1000] * 20
    result = build_risk_aware_paper_trade_decision(
        symbol="TCS",
        session="2026-08-17",
        closes=closes,
        highs=highs,
        lows=lows,
        volumes=volumes,
        equity=100000,
    )
    assert result.decision.status == "BLOCKED"
    assert result.decision.reason == "MARKET_REGIME_DATA_INSUFFICIENT"


def test_risk_engine_applies_portfolio_limits_after_trade_is_ready():
    closes, highs, lows, volumes = _series(up=True)
    existing = [
        PortfolioPosition("INFY", 59000, 500, "IT"),
    ]
    result = build_risk_aware_paper_trade_decision(
        symbol="TCS",
        session="2026-08-17",
        closes=closes,
        highs=highs,
        lows=lows,
        volumes=volumes,
        equity=100000,
        existing_positions=existing,
        sector="IT",
    )
    assert result.portfolio_allowed is False
    assert result.decision.status == "BLOCKED"
    assert result.decision.reason in {"TOTAL_EXPOSURE_LIMIT", "SECTOR_EXPOSURE_LIMIT"}
