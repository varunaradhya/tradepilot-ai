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
