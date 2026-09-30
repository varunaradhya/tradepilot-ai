from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.operational_audit_event import OperationalAuditEvent
from app.services.operational_audit import list_recent_events, record_event


def test_recent_audit_events_are_scoped_to_user():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        record_event(db, "USER_ONE_EVENT", user_id=1, payload={"ok": True})
        record_event(db, "USER_TWO_EVENT", user_id=2, payload={"ok": True})

        user_one = list_recent_events(db, user_id=1)
        user_two = list_recent_events(db, user_id=2)

        assert [event["event_type"] for event in user_one] == ["USER_ONE_EVENT"]
        assert [event["event_type"] for event in user_two] == ["USER_TWO_EVENT"]
    finally:
        db.close()
        engine.dispose()
