import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import Base
from app.models.paper_historical_run import PaperHistoricalRun


def test_historical_run_unique_key_is_database_enforced():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[PaperHistoricalRun.__table__])

    with Session(engine) as db:
        db.add(
            PaperHistoricalRun(
                user_id=7,
                symbol="RELIANCE",
                session="2026-08-28",
                interval="5",
                strategy_version="V1",
            )
        )
        db.commit()

        db.add(
            PaperHistoricalRun(
                user_id=7,
                symbol="RELIANCE",
                session="2026-08-28",
                interval="5",
                strategy_version="V1",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
