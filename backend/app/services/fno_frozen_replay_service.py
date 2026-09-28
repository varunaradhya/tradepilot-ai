from __future__ import annotations

"""Replay entry point for verified frozen execution-grade evidence."""

from typing import Any, Sequence

from app.services.fno_execution_evidence_freeze_service import (
    FrozenExecutionEvidencePackage,
    verify_frozen_execution_evidence,
)
from app.services.fno_replay_service import replay_autonomous_option_decisions


def replay_frozen_execution_evidence(
    *,
    package: FrozenExecutionEvidencePackage,
    underlying: dict[str, Any],
    bars: Sequence[dict[str, Any]],
    lot_size: int,
) -> list[dict[str, Any]]:
    """Replay only after verifying the frozen package and timestamp alignment."""
    if not verify_frozen_execution_evidence(package):
        raise ValueError("frozen execution evidence package failed integrity verification")

    snapshot_by_timestamp = {
        int(snapshot["timestamp"]): snapshot for snapshot in package.snapshots
    }
    if len(snapshot_by_timestamp) != len(package.snapshots):
        raise ValueError("frozen execution evidence contains duplicate snapshot timestamps")

    bar_timestamps: list[int] = []
    for bar in bars:
        try:
            bar_timestamps.append(int(float(bar["timestamp"])))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("replay bars require numeric timestamps") from exc

    if len(bar_timestamps) != len(set(bar_timestamps)):
        raise ValueError("replay bars contain duplicate timestamps")

    snapshots: list[dict[str, Any]] = []
    for timestamp in bar_timestamps:
        snapshot = snapshot_by_timestamp.get(timestamp)
        if snapshot is None:
            raise ValueError(
                f"frozen execution evidence missing snapshot for bar timestamp {timestamp}"
            )
        if snapshot.get("execution_grade") is not True:
            raise ValueError("replay requires execution-grade snapshots")
        snapshots.append(snapshot)

    return replay_autonomous_option_decisions(
        underlying=underlying,
        bars=bars,
        option_chain_snapshots=snapshots,
        lot_size=lot_size,
    )
