import pytest

from app.services.paper_trading_service import close_paper_trade, open_paper_trade, update_paper_trade


class FakeDB:
    def add(self, obj):
        self.obj = obj

    def commit(self):
        pass

    def refresh(self, obj):
        pass


def test_open_paper_trade_rejects_non_finite_prices():
    with pytest.raises(ValueError, match="Invalid paper trade parameters"):
        open_paper_trade(FakeDB(), 1, symbol="RELIANCE", quantity=1, entry_price=float("nan"), stop_price=90, target_price=120)


def test_update_paper_trade_rejects_invalid_market_range():
    trade = type("Trade", (), {"status": "OPEN", "stop_price": 90, "target_price": 120})()
    with pytest.raises(ValueError, match="Invalid market range"):
        update_paper_trade(FakeDB(), trade, 100, market_high=95, market_low=105)


def test_close_paper_trade_normalizes_reason():
    trade = type("Trade", (), {"status": "OPEN", "entry_price": 100, "quantity": 2})()
    result = close_paper_trade(FakeDB(), trade, 110, " manual ")
    assert result.reason == "MANUAL"
    assert result.pnl == 20
    assert result.status == "CLOSED"
