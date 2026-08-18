from __future__ import annotations

from typing import Any


def reconcile_paper_ledger(*, persisted_trades: list[Any], engine_trades: list[dict[str, Any]], engine_position: dict[str, Any] | None) -> dict[str, Any]:
    persisted_closed = [t for t in persisted_trades if getattr(t, "status", None) == "CLOSED"]
    persisted_open = [t for t in persisted_trades if getattr(t, "status", None) == "OPEN"]
    persisted_realized = round(sum(float(getattr(t, "pnl", 0.0) or 0.0) for t in persisted_closed), 2)
    engine_realized = round(sum(float(t.get("net_pnl", t.get("pnl", 0.0)) or 0.0) for t in engine_trades), 2)

    engine_open_symbol = str((engine_position or {}).get("symbol") or "").upper()
    persisted_open_symbols = sorted(str(getattr(t, "symbol", "")).upper() for t in persisted_open)
    position_consistent = (engine_position is None and not persisted_open) or (
        engine_position is not None and len(persisted_open) == 0
    )

    return {
        "status": "CONSISTENT" if abs(persisted_realized - engine_realized) <= 0.01 and position_consistent else "DIVERGED",
        "persisted_closed_trades": len(persisted_closed),
        "engine_closed_trades": len(engine_trades),
        "persisted_realized_pnl": persisted_realized,
        "engine_realized_pnl": engine_realized,
        "realized_pnl_delta": round(persisted_realized - engine_realized, 2),
        "engine_open_symbol": engine_open_symbol or None,
        "persisted_open_symbols": persisted_open_symbols,
        "position_consistent": position_consistent,
    }
