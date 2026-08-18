from __future__ import annotations

from math import isclose
from typing import Any, Sequence


def reconcile_paper_state(state: dict[str, Any], ledger_trades: Sequence[Any], tolerance: float = 0.01) -> dict[str, Any]:
    """Compare persisted engine state with the authoritative paper-trade ledger.

    A mismatch is a hard safety signal. Callers should stop new paper entries until
    the state is reconciled rather than attempting to repair financial values in-place.
    """
    if tolerance < 0:
        raise ValueError("tolerance must be non-negative")
    engine_trades = state.get("trades") or []
    ledger = list(ledger_trades)
    reasons: list[str] = []
    if len(engine_trades) != len(ledger):
        reasons.append("TRADE_COUNT_MISMATCH")

    comparable = min(len(engine_trades), len(ledger))
    for index in range(comparable):
        expected = engine_trades[index]
        actual = ledger[index]
        actual_symbol = str(getattr(actual, "symbol", "")).strip().upper()
        expected_symbol = str(expected.get("symbol") or "").strip().upper()
        if expected_symbol and actual_symbol and expected_symbol != actual_symbol:
            reasons.append(f"TRADE_{index}_SYMBOL_MISMATCH")
        if int(expected.get("quantity", 0)) != int(getattr(actual, "quantity", 0)):
            reasons.append(f"TRADE_{index}_QUANTITY_MISMATCH")
        if not isclose(float(expected.get("net_pnl", expected.get("pnl", 0.0))), float(getattr(actual, "pnl", 0.0)), abs_tol=tolerance):
            reasons.append(f"TRADE_{index}_PNL_MISMATCH")
        expected_status = "CLOSED"
        actual_status = str(getattr(actual, "status", "")).upper()
        if actual_status and actual_status != expected_status:
            reasons.append(f"TRADE_{index}_STATUS_MISMATCH")

    open_position = state.get("open_position")
    open_ledger = [trade for trade in ledger if str(getattr(trade, "status", "")).upper() == "OPEN"]
    if open_position is not None and len(open_ledger) != 1:
        reasons.append("OPEN_POSITION_LEDGER_MISMATCH")
    if open_position is None and open_ledger:
        reasons.append("ORPHAN_OPEN_LEDGER_POSITION")
    if float(state.get("realized_pnl", 0.0)) < 0 and not ledger:
        reasons.append("REALIZED_PNL_WITHOUT_LEDGER")

    return {"status": "RECONCILED" if not reasons else "HALT_AND_RECONCILE", "reasons": reasons}
