from types import SimpleNamespace

from app.services.paper_reconciliation import reconcile_paper_state


def trade(symbol, quantity, pnl, status="CLOSED"):
    return SimpleNamespace(symbol=symbol, quantity=quantity, pnl=pnl, status=status)


def test_reconciliation_is_independent_of_ledger_order():
    state = {
        "trades": [
            {"symbol": "INFY", "quantity": 5, "net_pnl": -20.0, "status": "CLOSED"},
            {"symbol": "TCS", "quantity": 2, "net_pnl": 40.0, "status": "CLOSED"},
        ]
    }
    result = reconcile_paper_state(
        state,
        [trade("TCS", 2, 40.0), trade("INFY", 5, -20.0)],
    )
    assert result["status"] == "RECONCILED"
    assert result["reasons"] == []


def test_reconciliation_fails_closed_for_invalid_trade_data():
    state = {"trades": [{"symbol": "TCS", "quantity": "not-a-number", "net_pnl": 10.0}]}
    result = reconcile_paper_state(state, [trade("TCS", 1, 10.0)])
    assert result["status"] == "HALT_AND_RECONCILE"
    assert result["reasons"] == ["INVALID_TRADE_RECONCILIATION_DATA"]


def test_reconciliation_detects_orphan_open_position():
    result = reconcile_paper_state(
        {"trades": [], "open_position": None},
        [trade("RELIANCE", 10, 0.0, "OPEN")],
    )
    assert result["status"] == "HALT_AND_RECONCILE"
    assert "TRADE_COUNT_MISMATCH" in result["reasons"]
    assert "ORPHAN_OPEN_LEDGER_POSITION" in result["reasons"]


def test_reconciliation_rejects_invalid_tolerance():
    try:
        reconcile_paper_state({}, [], tolerance=-0.01)
    except ValueError:
        pass
    else:
        raise AssertionError("negative tolerance must be rejected")
