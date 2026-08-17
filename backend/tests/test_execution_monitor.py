from app.services.execution_monitor import ExecutionLimits, ExecutionMonitor


def test_stale_signal_is_blocked():
    monitor = ExecutionMonitor(ExecutionLimits(max_signal_age_ms=1000))
    decision = monitor.record_signal(1001)
    assert not decision.allowed
    assert decision.reason == "STALE_SIGNAL"
    assert monitor.health.stale_signals == 1


def test_fresh_data_and_signal_are_allowed():
    monitor = ExecutionMonitor()
    assert monitor.check_data_freshness(100).allowed
    assert monitor.record_signal(100).allowed
    assert monitor.check_signal_latency(20).allowed
    assert monitor.check_risk_latency(5).allowed
    assert monitor.check_order_ack(100).allowed


def test_latency_breaches_fail_closed():
    monitor = ExecutionMonitor(ExecutionLimits(max_signal_eval_ms=50, max_risk_eval_ms=10, max_order_ack_ms=100))
    assert monitor.check_signal_latency(51).reason == "SIGNAL_EVALUATION_TOO_SLOW"
    assert monitor.check_risk_latency(11).reason == "RISK_EVALUATION_TOO_SLOW"
    assert monitor.check_order_ack(101).reason == "ORDER_ACK_TIMEOUT"


def test_stale_market_data_is_blocked():
    monitor = ExecutionMonitor(ExecutionLimits(max_data_age_ms=500))
    decision = monitor.check_data_freshness(501)
    assert not decision.allowed
    assert monitor.health.data_stale_events == 1
