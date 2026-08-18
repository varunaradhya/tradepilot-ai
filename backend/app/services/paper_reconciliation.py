from __future__ import annotations

from math import isclose, isfinite
from typing import Any, Sequence


def _normalise_trade(value: Any) -> tuple[str, int, float, str]:
    """Return a deterministic comparison key for persisted/ledger trades."""
    if isinstance(value, dict):
        symbol = value.get("symbol")
        quantity = value.get("quantity", 0)
        pnl = value.get("net_pnl", value.get("pnl", 0.0))
        status = value.get("status", "CLOSED")
    else:
        symbol = getattr(value, "symbol", "")
        quantity = getattr(value, "quantity", 0)
        pnl = getattr(value, "pnl", 0.0)
        status = getattr(value, "status", "")

    return (
        str(symbol or "").strip().upper(),
        int(quantity),
        round(float(pnl), 8),
        str(status or "").strip().upper(),
    )


def reconcile_paper_state(
    state: dict[str, Any],
    ledger_trades: Sequence[Any],
    tolerance: float = 0.01,
) -> dict[str, Any]:
    """Compare persisted engine state with the authoritative paper ledger.

    Comparison is order-independent so database retrieval order cannot create a
    false reconciliation failure. Invalid numeric values fail closed instead of
    crashing the monitoring endpoint.
    """
    if tolerance < 0 or not isfinite(tolerance):
        raise ValueError("tolerance must be a finite non-negative number")

    engine_trades = state.get("trades") or []
    ledger = list(ledger_trades)
    reasons: list[str] = []

    try:
        engine_keys = sorted(_normalise_trade(trade) for trade in engine_trades)
        ledger_keys = sorted(_normalise_trade(trade) for trade in ledger)
    except (TypeError, ValueError, OverflowError):
        return {
            "status": "HALT_AND_RECONCILE",
            "reasons": ["INVALID_TRADE_RECONCILIATION_DATA"],
        }

    if len(engine_keys) != len(ledger_keys):
        reasons.append("TRADE_COUNT_MISMATCH")

    if len(engine_keys) == len(ledger_keys):
        for index, (expected, actual) in enumerate(zip(engine_keys, ledger_keys)):
            if expected[0] != actual[0]:
                reasons.append(f"TRADE_{index}_SYMBOL_MISMATCH")
            if expected[1] != actual[1]:
                reasons.append(f"TRADE_{index}_QUANTITY_MISMATCH")
            if not isclose(expected[2], actual[2], abs_tol=tolerance):
                reasons.append(f"TRADE_{index}_PNL_MISMATCH")
            if expected[3] != actual[3]:
                reasons.append(f"TRADE_{index}_STATUS_MISMATCH")

    open_position = state.get("open_position")
    open_ledger = [
        trade for trade in ledger
        if str(getattr(trade, "status", "")).upper() == "OPEN"
    ]
    if open_position is not None and len(open_ledger) != 1:
        reasons.append("OPEN_POSITION_LEDGER_MISMATCH")
    if open_position is None and open_ledger:
        reasons.append("ORPHAN_OPEN_LEDGER_POSITION")
    if float(state.get("realized_pnl", 0.0)) != 0.0 and not ledger:
        reasons.append("REALIZED_PNL_WITHOUT_LEDGER")

    return {
        "status": "RECONCILED" if not reasons else "HALT_AND_RECONCILE",
        "reasons": reasons,
    }
