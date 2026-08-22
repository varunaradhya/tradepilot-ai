from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any, Sequence


@dataclass(frozen=True)
class HistoricalFNODataConfig:
    require_timestamp: bool = True
    require_bid_ask_for_execution: bool = True
    reject_future_quotes: bool = True


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def validate_historical_snapshot(
    *,
    snapshot: dict[str, Any],
    decision_timestamp: float,
    config: HistoricalFNODataConfig = HistoricalFNODataConfig(),
) -> dict[str, Any]:
    """Validate one immutable historical option-chain snapshot before replay.

    A snapshot is usable only when its timestamp is known and it does not
    contain quotes from after the decision time. Execution contracts must have
    a valid bid/ask pair when configured for realistic fills.
    """
    raw_timestamp = snapshot.get("timestamp")
    timestamp = _number(raw_timestamp)
    if config.require_timestamp and timestamp is None:
        return {"valid": False, "reason": "MISSING_SNAPSHOT_TIMESTAMP"}
    if timestamp is not None and config.reject_future_quotes and timestamp > decision_timestamp:
        return {"valid": False, "reason": "FUTURE_QUOTE"}

    contracts = 0
    executable = 0
    for strike, pair in (snapshot.get("oc") or {}).items():
        if not isinstance(pair, dict):
            continue
        for option_type in ("ce", "pe"):
            contract = pair.get(option_type)
            if not isinstance(contract, dict):
                continue
            contracts += 1
            bid = _number(contract.get("top_bid_price", contract.get("bid")))
            ask = _number(contract.get("top_ask_price", contract.get("ask")))
            if bid is not None and ask is not None and bid > 0 and ask > 0 and bid <= ask:
                executable += 1
            elif config.require_bid_ask_for_execution:
                continue

    if contracts == 0:
        return {"valid": False, "reason": "EMPTY_OPTION_CHAIN", "contracts": 0, "executable_contracts": 0}
    if config.require_bid_ask_for_execution and executable == 0:
        return {"valid": False, "reason": "NO_EXECUTABLE_QUOTES", "contracts": contracts, "executable_contracts": executable}
    return {"valid": True, "reason": "OK", "contracts": contracts, "executable_contracts": executable, "timestamp": timestamp}


def validate_historical_dataset(
    *,
    bars: Sequence[dict[str, Any]],
    snapshots: Sequence[dict[str, Any]],
    config: HistoricalFNODataConfig = HistoricalFNODataConfig(),
) -> dict[str, Any]:
    """Validate aligned underlying bars and historical option snapshots.

    This is intentionally a validation/ingestion boundary, not a strategy
    optimizer. Invalid rows are reported rather than silently repaired.
    """
    if len(bars) != len(snapshots):
        return {"valid": False, "reason": "LENGTH_MISMATCH", "bars": len(bars), "snapshots": len(snapshots)}

    invalid: list[dict[str, Any]] = []
    previous_timestamp: float | None = None
    for index, (bar, snapshot) in enumerate(zip(bars, snapshots)):
        timestamp = _number(bar.get("timestamp"))
        if timestamp is None:
            invalid.append({"index": index, "reason": "MISSING_BAR_TIMESTAMP"})
            continue
        if previous_timestamp is not None and timestamp <= previous_timestamp:
            invalid.append({"index": index, "reason": "NON_MONOTONIC_BAR_TIMESTAMP"})
        previous_timestamp = timestamp
        result = validate_historical_snapshot(snapshot=snapshot, decision_timestamp=timestamp, config=config)
        if not result["valid"]:
            invalid.append({"index": index, "reason": result["reason"]})

    return {
        "valid": not invalid,
        "bars": len(bars),
        "snapshots": len(snapshots),
        "invalid_rows": invalid,
        "invalid_count": len(invalid),
    }
