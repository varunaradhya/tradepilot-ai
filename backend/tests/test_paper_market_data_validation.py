import pytest

from app.services.paper_market_service import PaperMarketState


def test_market_state_rejects_non_finite_ohlcv():
    state = PaperMarketState()
    with pytest.raises(ValueError, match="finite"):
        state.append(100.0, 101.0, 99.0, float("nan"), 1000.0)


def test_market_state_rejects_non_positive_ohlc():
    state = PaperMarketState()
    with pytest.raises(ValueError, match="positive"):
        state.append(0.0, 101.0, 99.0, 100.0, 1000.0)
