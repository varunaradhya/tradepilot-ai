from app.core.production_safety import SafetyViolation, assert_live_order_blocked, assert_simulation_only

def test_live_order_gate_is_permanently_blocked():
    try:
        assert_live_order_blocked()
    except SafetyViolation:
        return
    raise AssertionError("live order gate must always reject")

def test_unknown_execution_mode_is_rejected():
    try:
        assert_simulation_only("LIVE")
    except SafetyViolation:
        return
    raise AssertionError("unknown/live execution mode must be rejected")

def test_simulation_mode_is_accepted():
    assert_simulation_only("SIMULATION_ONLY")
