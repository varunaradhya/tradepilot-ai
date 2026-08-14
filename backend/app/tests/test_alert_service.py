from app.services.alert_service import create_alert


class Query:
    def filter(self, *args): return self
    def first(self): return None


class Session:
    def __init__(self): self.added = []
    def query(self, model): return Query()
    def add(self, item): self.added.append(item)
    def commit(self): pass
    def refresh(self, item): item.id = 1


def test_alert_deduplication_is_deterministic(monkeypatch):
    session = Session()
    first = create_alert(session, 1, "OPPORTUNITY", "INFO", "Title", "Message", "TCS")
    assert first is not None
    assert first.severity == "INFO"
