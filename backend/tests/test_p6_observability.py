from app.services.observability import RequestObservability, slo_snapshot
from app.services.sandbox_credentials import sandbox_credential_status


def test_request_observability_tracks_failures_and_latency():
    telemetry = RequestObservability(window_seconds=300)
    telemetry.observe(12.0)
    telemetry.observe(28.0, failed=True)
    snapshot = telemetry.snapshot()
    assert snapshot["requests"] == 2
    assert snapshot["failures"] == 1
    assert snapshot["error_rate_percent"] == 50.0
    assert snapshot["average_latency_ms"] == 20.0
    assert snapshot["status"] == "degraded"


def test_slo_snapshot_fails_closed_for_unhealthy_dependencies():
    result = slo_snapshot(database_available=False, market_data_fresh=False, kill_switch_active=True)
    assert result["status"] == "degraded"
    assert result["safety"]["kill_switch_active"] is True
    assert result["safety"]["live_execution_enabled"] is False


def test_dhan_sandbox_credentials_never_expose_values(monkeypatch):
    monkeypatch.setenv("TRADEPILOT_DHAN_SANDBOX_CLIENT_ID", "client-secret-value")
    monkeypatch.delenv("TRADEPILOT_DHAN_SANDBOX_ACCESS_TOKEN", raising=False)
    result = sandbox_credential_status("dhan")
    assert result["configured"] is False
    assert "TRADEPILOT_DHAN_SANDBOX_ACCESS_TOKEN" in result["missing"]
    assert "client-secret-value" not in str(result)
    assert result["secret_values_exposed"] is False
    assert result["live_execution_allowed"] is False


def test_unsupported_sandbox_is_safe():
    result = sandbox_credential_status("unknown")
    assert result["supported"] is False
    assert result["configured"] is False
    assert result["live_execution_allowed"] is False
