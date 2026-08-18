from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.operational_kill_switch import OperationalKillSwitch
from app.services.kill_switch_service import activate_kill_switch, get_kill_switch, kill_switch_status


def test_kill_switch_is_durable_and_fail_closed():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=[OperationalKillSwitch.__table__])
    session = sessionmaker(bind=engine)()

    initial = get_kill_switch(session)
    assert initial.active is True

    activated = activate_kill_switch(session, reason="STALE_FEED", user_id=7)
    assert activated.active is True
    assert activated.reason == "STALE_FEED"

    status = kill_switch_status(session)
    assert status["active"] is True
    assert status["reason"] == "STALE_FEED"
    assert status["activated_by_user_id"] == 7

    session.close()
