from datetime import datetime, timezone

from app.services.strategy_paper_authorization import authorize_strategy, get_active_authorization, revoke_strategy


class _Query:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []

    def filter(self, *conditions):
        self.filters.extend(conditions)
        return self

    def first(self):
        return self.rows[0] if self.rows else None


class _DB:
    def __init__(self):
        self.rows = []
        self.added = []

    def query(self, model):
        return _Query(self.rows)

    def add(self, record):
        record.id = len(self.rows) + 1
        self.rows.append(record)
        self.added.append(record)

    def commit(self):
        pass

    def refresh(self, record):
        if getattr(record, "authorized_at", None) is None:
            record.authorized_at = datetime.now(timezone.utc)


def test_authorization_is_created_with_fingerprint_and_evidence():
    db = _DB()
    record = authorize_strategy(
        db,
        7,
        symbol="reliance",
        interval="5",
        strategy_version="V1",
        fingerprint="abcdef1234567890",
        evidence={"qualification": {"status": "PAPER_CANDIDATE"}},
    )
    assert record.id == 1
    assert record.symbol == "RELIANCE"
    assert record.status == "AUTHORIZED"
    assert record.fingerprint == "abcdef1234567890"
    assert record.evidence_json.startswith("{")


def test_active_lookup_and_revoke_fail_closed_after_revocation():
    db = _DB()
    authorize_strategy(
        db,
        7,
        symbol="RELIANCE",
        interval="5",
        strategy_version="V1",
        fingerprint="abcdef1234567890",
        evidence={"ok": True},
    )
    assert get_active_authorization(db, 7, symbol="RELIANCE", interval="5", strategy_version="V1") is not None
    assert revoke_strategy(db, 7, symbol="RELIANCE", interval="5", strategy_version="V1") is True
    assert db.rows[0].status == "REVOKED"
