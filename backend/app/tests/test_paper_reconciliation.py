from types import SimpleNamespace

from app.services.paper_reconciliation import reconcile_paper_state


def test_reconciliation_passes_matching_closed_ledger():
    state = {"realized_pnl": 47.92, "trades": [{"symbol": "TCS", "quantity": 10, "net_pnl": 47.92}], "open_position": None}
    ledger = [SimpleNamespace(symbol="TCS", quantity=10, pnl=47.92, status="CLOSED")]
    assert reconcile_paper_state(state, ledger)["status"] == "RECONCILED"


def test_reconciliation_halts_on_pnl_mismatch():
    state = {"realized_pnl": 47.92, "trades": [{"symbol": "TCS", "quantity": 10, "net_pnl": 47.92}], "open_position": None}
    ledger = [SimpleNamespace(symbol="TCS", quantity=10, pnl=50.0, status="CLOSED")]
    result = reconcile_paper_state(state, ledger)
    assert result["status"] == "HALT_AND_RECONCILE"
    assert "TRADE_0_PNL_MISMATCH" in result["reasons"]


def test_reconciliation_halts_on_orphan_open_ledger_position():
    state = {"realized_pnl": 0.0, "trades": [], "open_position": None}
    ledger = [SimpleNamespace(symbol="INFY", quantity=5, pnl=0.0, status="OPEN")]
    result = reconcile_paper_state(state, ledger)
    assert result["status"] == "HALT_AND_RECONCILE"
    assert "ORPHAN_OPEN_LEDGER_POSITION" in result["reasons"]
