from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.services.intraday_evidence_aggregation import aggregate_paper_performance
from app.services.paper_reconciliation import reconcile_paper_state


@dataclass(frozen=True)
class PaperMonitoringThresholds:
    max_reconciliation_mismatches: int = 0
    min_expected_paper_trades: int = 1


def build_paper_monitoring_snapshot(
    trades: list[Any],
    session_state: dict[str, Any] | None = None,
    thresholds: PaperMonitoringThresholds = PaperMonitoringThresholds(),
) -> dict[str, Any]:
    """Build the canonical read-only paper-session health snapshot.

    Monitoring never places, modifies, or cancels broker orders. Reconciliation
    failures are fail-closed and surfaced as a halt condition.
    """
    if thresholds.max_reconciliation_mismatches < 0:
        raise ValueError("max_reconciliation_mismatches must be non-negative")
    if thresholds.min_expected_paper_trades < 0:
        raise ValueError("min_expected_paper_trades must be non-negative")

    state = session_state or {}
    reconciliation = reconcile_paper_state(state, trades)
    reasons = reconciliation.get("reasons", [])
    halt = len(reasons) > thresholds.max_reconciliation_mismatches
    performance = aggregate_paper_performance(trades)

    open_trades = [trade for trade in trades if str(getattr(trade, "status", "")).upper() == "OPEN"]
    closed_trades = [trade for trade in trades if str(getattr(trade, "status", "")).upper() == "CLOSED"]

    alerts: list[dict[str, str]] = []
    if halt:
        alerts.append({
            "code": "HALT_AND_RECONCILE",
            "severity": "CRITICAL",
            "message": "Paper state and ledger reconciliation failed.",
        })

    if len(closed_trades) < thresholds.min_expected_paper_trades:
        alerts.append({
            "code": "INSUFFICIENT_PAPER_EVIDENCE",
            "severity": "WARNING",
            "message": "Paper trading evidence is below the configured minimum.",
        })

    return {
        "status": "HALT_AND_RECONCILE" if halt else "HEALTHY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "SIMULATION_ONLY",
        "safety": {
            "broker_orders_enabled": False,
            "halt_required": halt,
            "mismatch_count": len(reasons),
            "minimum_expected_paper_trades": thresholds.min_expected_paper_trades,
        },
        "session": {
            "state": state.get("state", "UNKNOWN"),
            "session": state.get("session"),
            "symbol": state.get("symbol"),
            "last_bar_timestamp": state.get("last_bar_timestamp"),
        },
        "ledger": {
            "total_trades": len(trades),
            "open_trades": len(open_trades),
            "closed_trades": len(closed_trades),
            "reconciliation": reconciliation,
        },
        "performance": performance,
        "alerts": alerts,
    }
