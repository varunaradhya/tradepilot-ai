from pathlib import Path


def test_portfolio_sync_serializes_same_broker_connection():
    source = Path("app/services/portfolio_sync_service.py").read_text(encoding="utf-8")
    start = source.index("def sync_dhan_portfolio(")
    section = source[start:]
    assert "BrokerConnection.id == connection.id" in section
    assert "BrokerConnection.user_id == connection.user_id" in section
    assert ".with_for_update()" in section


def test_malformed_broker_trade_timestamp_is_not_replaced_with_new_identity():
    source = Path("app/services/portfolio_sync_service.py").read_text(encoding="utf-8")
    start = source.index("def _sync_trades(")
    end = source.index("\ndef sync_dhan_portfolio(", start)
    section = source[start:end]
    assert "Do not synthesize a new timestamp" in section
    assert "continue" in section
    assert "if transaction_date is None:" in section


def test_holding_symbol_is_unique_per_user_at_database_boundary():
    model = Path("app/models/holding.py").read_text(encoding="utf-8")
    migration = next(
        Path("alembic/versions").glob("20260929_0017_holding_uniqueness.py")
    ).read_text(encoding="utf-8")
    service = Path("app/services/portfolio_service.py").read_text(encoding="utf-8")
    assert 'UniqueConstraint("user_id", "symbol", name="uq_holdings_user_symbol")' in model
    assert '"uq_holdings_user_symbol"' in migration
    assert "unique=True" in migration
    assert "Holding.user_id == user_id" in service
    assert "Holding.symbol == normalized_symbol" in service
    assert "IntegrityError" in service


def test_transaction_mutations_lock_user_before_rebuilding_holdings():
    source = Path("app/services/transaction_service.py").read_text(encoding="utf-8")
    assert "from app.models.user import User" in source
    assert "def _lock_user" in source
    assert "db.query(User).filter(User.id == user_id).with_for_update().one()" in source
    assert source.index("_lock_user(db, user_id)") < source.index("db.commit()")
