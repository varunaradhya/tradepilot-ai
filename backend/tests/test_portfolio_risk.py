from app.services.portfolio_risk import (
    PortfolioPosition,
    PortfolioRiskConfig,
    evaluate_new_position,
)


def test_total_risk_limit_blocks_correlated_addition():
    result = evaluate_new_position(
        capital=100000,
        proposed_market_value=10000,
        proposed_risk_value=800,
        proposed_sector="BANKING",
        existing_positions=[
            PortfolioPosition("HDFCBANK", 20000, 700, "BANKING"),
            PortfolioPosition("ICICIBANK", 20000, 700, "BANKING"),
        ],
        config=PortfolioRiskConfig(max_total_risk_fraction=0.02),
    )
    assert not result.allowed
    assert result.reason == "TOTAL_RISK_LIMIT"


def test_sector_limit_blocks_concentration():
    result = evaluate_new_position(
        capital=100000,
        proposed_market_value=10000,
        proposed_risk_value=200,
        proposed_sector="BANKING",
        existing_positions=[
            PortfolioPosition("HDFCBANK", 20000, 300, "BANKING"),
            PortfolioPosition("ICICIBANK", 10000, 300, "BANKING"),
        ],
        config=PortfolioRiskConfig(max_sector_exposure_fraction=0.30),
    )
    assert not result.allowed
    assert result.reason == "SECTOR_EXPOSURE_LIMIT"


def test_single_symbol_limit_blocks_oversized_position():
    result = evaluate_new_position(
        capital=100000,
        proposed_market_value=25000,
        proposed_risk_value=500,
        proposed_sector="IT",
        existing_positions=[],
    )
    assert not result.allowed
    assert result.reason == "SINGLE_SYMBOL_EXPOSURE_LIMIT"


def test_safe_position_is_approved():
    result = evaluate_new_position(
        capital=100000,
        proposed_market_value=10000,
        proposed_risk_value=300,
        proposed_sector="IT",
        existing_positions=[],
    )
    assert result.allowed
    assert result.reason == "APPROVED"
