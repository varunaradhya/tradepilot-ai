from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum


class ExecutionMode(StrEnum):
    SIMULATION_ONLY = "SIMULATION_ONLY"
    LIVE_LOCKED = "LIVE_LOCKED"


class SafetyViolation(RuntimeError):
    """Raised when an operation crosses a production safety boundary."""


@dataclass(frozen=True)
class OperationalSnapshot:
    mode: ExecutionMode = ExecutionMode.SIMULATION_ONLY
    market_data_fresh: bool = False
    reconciliation_healthy: bool = False
    strategy_ready: bool = False
    risk_limits_healthy: bool = False
    broker_connected: bool = False
    kill_switch_active: bool = True
    checked_at: datetime | None = None

    @property
    def live_order_allowed(self) -> bool:
        return False

    @property
    def paper_operations_allowed(self) -> bool:
        return self.mode == ExecutionMode.SIMULATION_ONLY and self.market_data_fresh and self.reconciliation_healthy and not self.kill_switch_active

    def as_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "market_data_fresh": self.market_data_fresh,
            "reconciliation_healthy": self.reconciliation_healthy,
            "strategy_ready": self.strategy_ready,
            "risk_limits_healthy": self.risk_limits_healthy,
            "broker_connected": self.broker_connected,
            "kill_switch_active": self.kill_switch_active,
            "paper_operations_allowed": self.paper_operations_allowed,
            "live_order_allowed": False,
            "checked_at": (self.checked_at or datetime.now(timezone.utc)).isoformat(),
        }


def assert_live_order_blocked() -> None:
    """Permanent P4 guard: no code path may place a live order yet."""
    raise SafetyViolation("Live order execution is locked by TradePilot P4 safety policy")


def build_operational_snapshot(*, market_data_fresh: bool, reconciliation_healthy: bool, strategy_ready: bool = False, risk_limits_healthy: bool = False, broker_connected: bool = False, kill_switch_active: bool = True) -> OperationalSnapshot:
    return OperationalSnapshot(
        market_data_fresh=market_data_fresh,
        reconciliation_healthy=reconciliation_healthy,
        strategy_ready=strategy_ready,
        risk_limits_healthy=risk_limits_healthy,
        broker_connected=broker_connected,
        kill_switch_active=kill_switch_active,
        checked_at=datetime.now(timezone.utc),
    )
