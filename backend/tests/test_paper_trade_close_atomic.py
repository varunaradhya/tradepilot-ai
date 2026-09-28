from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.database import Base
from app.models.paper_trade import PaperTrade
from app.services.paper_trading_service import close_paper_trade

def test_close_is_idempotent():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine,tables=[PaperTrade.__table__])
    db=Session(engine)
    trade=PaperTrade(user_id=1,symbol="RELIANCE",side="BUY",status="OPEN",quantity=1,entry_price=100,stop_price=95,target_price=110,strategy_version="V1",asset_type="EQUITY")
    db.add(trade); db.commit(); db.refresh(trade)
    first=close_paper_trade(db,trade,108,"TARGET")
    second=close_paper_trade(db,trade,105,"MANUAL")
    assert first.status=="CLOSED"
    assert second.exit_price==108
    assert second.reason=="TARGET"
