from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.models.paper_session_state import PaperSessionState
from app.services.paper_session_state_service import load_paper_session_state, save_paper_session_state


def test_paper_session_state_round_trip():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[PaperSessionState.__table__])
    db = Session(engine)

    state = {"strategy_fingerprint": "abc12345", "engine": {"cash": 98765.43, "halted": False}}
    save_paper_session_state(db, 7, state)
    assert load_paper_session_state(db, 7) == state

    updated = {**state, "engine": {"cash": 98000.0, "halted": True}}
    save_paper_session_state(db, 7, updated)
    assert load_paper_session_state(db, 7) == updated
