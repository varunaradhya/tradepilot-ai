from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Any


@dataclass
class _Window:
    started: float
    requests: int = 0
    failures: int = 0
    total_latency_ms: float = 0.0
    max_latency_ms: float = 0.0


class RequestObservability:
    """Small bounded in-process request window for operational health signals.

    This intentionally exposes telemetry only; it cannot change trading state.
    Deployments with external metrics can scrape/forward the same snapshot.
    """

    def __init__(self, window_seconds: int = 300) -> None:
        self.window_seconds = max(30, int(window_seconds))
        self._lock = Lock()
        self._window = _Window(monotonic())

    def _roll(self, now: float) -> None:
        if now - self._window.started >= self.window_seconds:
            self._window = _Window(now)

    def observe(self, latency_ms: float, failed: bool = False) -> None:
        now = monotonic()
        with self._lock:
            self._roll(now)
            self._window.requests += 1
            self._window.failures += int(failed)
            self._window.total_latency_ms += max(0.0, latency_ms)
            self._window.max_latency_ms = max(self._window.max_latency_ms, latency_ms)

    def snapshot(self) -> dict[str, Any]:
        now = monotonic()
        with self._lock:
            self._roll(now)
            requests = self._window.requests
            failures = self._window.failures
            return {
                "window_seconds": self.window_seconds,
                "requests": requests,
                "failures": failures,
                "error_rate_percent": round((failures / requests) * 100, 3) if requests else 0.0,
                "average_latency_ms": round(self._window.total_latency_ms / requests, 2) if requests else 0.0,
                "max_latency_ms": round(self._window.max_latency_ms, 2),
                "status": "healthy" if failures == 0 else "degraded",
            }


OBSERVABILITY = RequestObservability()


def slo_snapshot(*, database_available: bool, market_data_fresh: bool, kill_switch_active: bool) -> dict[str, Any]:
    telemetry = OBSERVABILITY.snapshot()
    dependencies_ok = database_available and market_data_fresh
    return {
        "status": "healthy" if dependencies_ok and telemetry["status"] == "healthy" else "degraded",
        "safety": {
            "kill_switch_active": kill_switch_active,
            "live_execution_enabled": False,
        },
        "dependencies": {
            "database": "available" if database_available else "unavailable",
            "market_data": "fresh" if market_data_fresh else "unhealthy",
        },
        "slo": telemetry,
    }
