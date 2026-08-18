from types import SimpleNamespace

import pytest

from app.services.paper_monitoring import PaperMonitoringThresholds, build_paper_monitoring_snapshot


def _closed_trade():
    return SimpleNamespace(
        status="CLOSED",
        symbol="RELIANCE",
        quantity=10,
        pnl=100.0,
        created_at=None,
        closed_at=None,
        reason="TARGET",
    )


def test_monitoring_snapshot_is_simulation_only():
    snapshot = build_paper_monitoring_snapshot([_closed_trade()], {"trades": [{"symbol": "RELIANCE", "quantity": 10, "net_pnl": 100.0}]})
    assert snapshot["mode"] == "SIMULATION_ONLY"
    assert snapshot["safety"]["broker_orders_enabled"] is False
    assert snapshot["status"] == "HEALTHY"


def test_monitoring_halts_on_reconciliation_mismatch():
    trade = _closed_trade()
    snapshot = build_paper_monitoring_snapshot(
        [trade],
        {"trades": [{"symbol": "RELIANCE", "quantity": 11, "net_pnl": 100.0}]},
    )
    assert snapshot["status"] == "HALT_AND_RECONCILE"
    assert snapshot["safety"]["halt_required"] is True
    assert snapshot["alerts"][0]["code"] == "HALT_AND_RECONCILE"


def test_monitoring_warns_when_paper_evidence_is_insufficient():
    snapshot = build_paper_monitoring_snapshot(
        [_closed_trade()],
        {"trades": [{"symbol": "RELIANCE", "quantity": 10, "net_pnl": 100.0}]},
        PaperMonitoringThresholds(min_expected_paper_trades=2),
    )
    assert snapshot["status"] == "HEALTHY"
    assert any(alert["code"] == "INSUFFICIENT_PAPER_EVIDENCE" for alert in snapshot["alerts"])


def test_monitoring_rejects_invalid_thresholds():
    with pytest.raises(ValueError):
        build_paper_monitoring_snapshot([], thresholds=PaperMonitoringThresholds(max_reconciliation_mismatches=-1))
    with pytest.raises(ValueError):
        build_paper_monitoring_snapshot([], thresholds=PaperMonitoringThresholds(min_expected_paper_trades=-1))
