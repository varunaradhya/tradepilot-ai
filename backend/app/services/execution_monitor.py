from __future__ import annotations

from dataclasses import dataclass
from time import monotonic


@dataclass(frozen=True)
class ExecutionLimits:
    max_signal_age_ms: int = 1500
    max_data_age_ms: int = 3000
    max_order_ack_ms: int = 2000
    max_signal_eval_ms: int = 250
    max_risk_eval_ms: int = 25


@dataclass(frozen=True)
class ExecutionDecision:
    allowed: bool
    reason: str


@dataclass
class ExecutionHealth:
    last_market_event_ms: float | None = None
    last_signal_ms: float | None = None
    last_order_ack_ms: float | None = None
    rejected_orders: int = 0
    stale_signals: int = 0
    data_stale_events: int = 0


class ExecutionMonitor:
    """Small, dependency-free guard for live/paper execution paths.

    It does not place orders. It provides deterministic freshness and latency
    checks so the broker adapter can fail closed instead of submitting stale
    or unexpectedly slow decisions.
    """

    def __init__(self, limits: ExecutionLimits = ExecutionLimits()):
        self.limits = limits
        self.health = ExecutionHealth()

    @staticmethod
    def elapsed_ms(start: float) -> float:
        return max(0.0, (monotonic() - start) * 1000.0)

    def record_market_event(self) -> None:
        self.health.last_market_event_ms = monotonic() * 1000.0

    def record_signal(self, age_ms: float) -> ExecutionDecision:
        self.health.last_signal_ms = monotonic() * 1000.0
        if age_ms > self.limits.max_signal_age_ms:
            self.health.stale_signals += 1
            return ExecutionDecision(False, "STALE_SIGNAL")
        return ExecutionDecision(True, "SIGNAL_FRESH")

    def check_data_freshness(self, age_ms: float) -> ExecutionDecision:
        if age_ms > self.limits.max_data_age_ms:
            self.health.data_stale_events += 1
            return ExecutionDecision(False, "STALE_MARKET_DATA")
        return ExecutionDecision(True, "MARKET_DATA_FRESH")

    def check_signal_latency(self, latency_ms: float) -> ExecutionDecision:
        if latency_ms > self.limits.max_signal_eval_ms:
            return ExecutionDecision(False, "SIGNAL_EVALUATION_TOO_SLOW")
        return ExecutionDecision(True, "SIGNAL_EVALUATION_OK")

    def check_risk_latency(self, latency_ms: float) -> ExecutionDecision:
        if latency_ms > self.limits.max_risk_eval_ms:
            return ExecutionDecision(False, "RISK_EVALUATION_TOO_SLOW")
        return ExecutionDecision(True, "RISK_EVALUATION_OK")

    def check_order_ack(self, latency_ms: float) -> ExecutionDecision:
        self.health.last_order_ack_ms = monotonic() * 1000.0
        if latency_ms > self.limits.max_order_ack_ms:
            self.health.rejected_orders += 1
            return ExecutionDecision(False, "ORDER_ACK_TIMEOUT")
        return ExecutionDecision(True, "ORDER_ACK_OK")

    def snapshot(self) -> dict:
        return {
            "limits": {
                "max_signal_age_ms": self.limits.max_signal_age_ms,
                "max_data_age_ms": self.limits.max_data_age_ms,
                "max_order_ack_ms": self.limits.max_order_ack_ms,
                "max_signal_eval_ms": self.limits.max_signal_eval_ms,
                "max_risk_eval_ms": self.limits.max_risk_eval_ms,
            },
            "health": {
                "last_market_event_ms": self.health.last_market_event_ms,
                "last_signal_ms": self.health.last_signal_ms,
                "last_order_ack_ms": self.health.last_order_ack_ms,
                "rejected_orders": self.health.rejected_orders,
                "stale_signals": self.health.stale_signals,
                "data_stale_events": self.health.data_stale_events,
            },
        }
