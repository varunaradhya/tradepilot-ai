import pytest

from app.core.production_safety import SafetyViolation, build_operational_snapshot, assert_live_order_blocked


def test_live_orders_are_always_blocked():
    with pytest.raises(SafetyViolation):
        assert_live_order_blocked()


def test_operational_snapshot_fails_closed_by_default():
    snapshot = build_operational_snapshot(
        market_data_fresh=False,
        reconciliation_healthy=False,
        strategy_ready=False,
        risk_limits_healthy=False,
        broker_connected=False,
        kill_switch_active=True,
    )
    data = snapshot.as_dict()
    assert data["mode"] == "SIMULATION_ONLY"
    assert data["live_order_allowed"] is False
    assert data["paper_operations_allowed"] is False
    assert data["kill_switch_active"] is True


def test_paper_operations_require_fresh_data_reconciliation_and_kill_switch_clear():
    snapshot = build_operational_snapshot(
        market_data_fresh=True,
        reconciliation_healthy=True,
        strategy_ready=True,
        risk_limits_healthy=True,
        broker_connected=True,
        kill_switch_active=False,
    )
    assert snapshot.paper_operations_allowed is True
    assert snapshot.live_order_allowed is False
