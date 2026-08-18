from types import SimpleNamespace

from app.services.paper_monitoring import build_paper_monitoring_snapshot


def test_monitoring_snapshot_is_simulation_only():
    trades = [
        SimpleNamespace(status="CLOSED", symbol="RELIANCE", quantity=10, pnl=100.0, created_at=None, closed_at=None),
    ]
    snapshot = build_paper_monitoring_snapshot(trades)
    assert snapshot["mode"] == "SIMULATION_ONLY"
    assert snapshot["safety"]["broker_orders_enabled"] is False
    assert snapshot["status"] in {"HEALTHY", "HALT_AND_RECONCILE"}


def test_monitoring_halts_on_reconciliation_mismatch(monkeypatch):
    trades = [SimpleNamespace(status="CLOSED", symbol="RELIANCE", quantity=10, pnl=100.0, created_at=None, closed_at=None)]

    monkeypatch.setattr(
        "app.services.paper_monitoring.reconcile_paper_ledger",
        lambda _trades: {"status": "MISMATCH", "mismatches": ["quantity"]},
    )
    snapshot = build_paper_monitoring_snapshot(trades)
    assert snapshot["status"] == "HALT_AND_RECONCILE"
    assert snapshot["safety"]["halt_required"] is True
    assert snapshot["alerts"][0]["code"] == "HALT_AND_RECONCILE"
