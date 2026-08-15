from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.paper_trade import PaperTrade
from app.services.paper_trading_service import close_paper_trade, open_paper_trade, paper_summary, update_paper_trade


def _db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=[PaperTrade.__table__])
    return sessionmaker(bind=engine)()


def test_persistent_paper_trade_lifecycle():
    db = _db()
    trade = open_paper_trade(db, 1, symbol="TCS", quantity=10, entry_price=100, stop_price=95, target_price=110)
    assert trade.status == "OPEN"
    assert update_paper_trade(db, trade, 105).pnl == 50
    closed = update_paper_trade(db, trade, 111, market_high=111, market_low=109)
    assert closed.status == "CLOSED" and closed.reason == "TARGET" and closed.pnl == 100


def test_stop_has_priority_when_both_levels_touch():
    db = _db()
    trade = open_paper_trade(db, 1, symbol="INFY", quantity=1, entry_price=100, stop_price=95, target_price=110)
    closed = update_paper_trade(db, trade, 102, market_high=115, market_low=90)
    assert closed.reason == "STOP" and closed.exit_price == 95


def test_summary_tracks_realized_profit():
    db = _db()
    trade = open_paper_trade(db, 1, symbol="SBIN", quantity=2, entry_price=100, stop_price=95, target_price=110)
    closed = close_paper_trade(db, trade, 103)
    summary = paper_summary([closed])
    assert summary["realized_pnl"] == 6.0 and summary["win_rate_percent"] == 100.0


def test_invalid_stop_is_rejected():
    db = _db()
    try:
        open_paper_trade(db, 1, symbol="TCS", quantity=1, entry_price=100, stop_price=105, target_price=110)
    except ValueError as exc:
        assert "Stop price" in str(exc)
    else:
        raise AssertionError("invalid stop should be rejected")
