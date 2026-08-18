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
