from types import SimpleNamespace

from app.services.paper_ledger_reconciliation import reconcile_paper_ledger


def test_consistent_closed_ledger():
    persisted = [SimpleNamespace(status="CLOSED", pnl=47.92, symbol="RELIANCE")]
    result = reconcile_paper_ledger(
        persisted_trades=persisted,
        engine_trades=[{"net_pnl": 47.92}],
        engine_position=None,
    )
    assert result["status"] == "CONSISTENT"
    assert result["realized_pnl_delta"] == 0.0


def test_detects_realized_pnl_divergence():
    persisted = [SimpleNamespace(status="CLOSED", pnl=47.92, symbol="RELIANCE")]
    result = reconcile_paper_ledger(
        persisted_trades=persisted,
        engine_trades=[{"net_pnl": 50.0}],
        engine_position=None,
    )
    assert result["status"] == "DIVERGED"
    assert result["realized_pnl_delta"] == -2.08


def test_open_position_reconciliation_matches_symbol_and_security_id():
    from types import SimpleNamespace
    persisted = [SimpleNamespace(status="OPEN", pnl=0.0, symbol="NIFTY 2026-09-24 25000 CE", security_id="12345")]
    result = reconcile_paper_ledger(
        persisted_trades=persisted,
        engine_trades=[],
        engine_position={"symbol": "NIFTY 2026-09-24 25000 CE", "security_id": "12345"},
    )
    assert result["status"] == "CONSISTENT"
    assert result["position_consistent"] is True


def test_open_position_reconciliation_rejects_wrong_contract_identity():
    from types import SimpleNamespace
    persisted = [SimpleNamespace(status="OPEN", pnl=0.0, symbol="NIFTY 2026-09-24 25000 CE", security_id="12345")]
    result = reconcile_paper_ledger(
        persisted_trades=persisted,
        engine_trades=[],
        engine_position={"symbol": "NIFTY 2026-09-24 25000 PE", "security_id": "99999"},
    )
    assert result["status"] == "DIVERGED"
    assert result["position_consistent"] is False
