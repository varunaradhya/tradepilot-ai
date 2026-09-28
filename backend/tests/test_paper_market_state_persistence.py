from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.database import Base
from app.models.paper_market_state import PaperMarketState
from app.services.paper_market_state_service import save_market_state, load_market_state

def test_market_state_round_trip():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine,tables=[PaperMarketState.__table__])
    db=Session(engine)
    state={"opens":[100.0],"highs":[101.0],"lows":[99.0],"closes":[100.5],"volumes":[1000.0]}
    save_market_state(db,1,"2026-09-28","RELIANCE",state)
    assert load_market_state(db,1,"2026-09-28","RELIANCE")==state
