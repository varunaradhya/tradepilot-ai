from __future__ import annotations
from datetime import date
from typing import Iterable
from app.services.paper_dhan_service import run_dhan_paper_session
from app.services.paper_validation_service import (
    DEFAULT_VALIDATION_SYMBOLS, normalize_validation_symbols, validation_run_key,
    finalize_multi_symbol_validation_day, persist_validation_manifest,
)
from app.services.nse_equity_calendar import DEFAULT_NSE_EQUITY_CALENDAR

def run_daily_dhan_validation(db, user_id: int, symbols: Iterable[str] | None, session: date, interval: str = "5") -> dict:
    universe = normalize_validation_symbols(symbols or DEFAULT_VALIDATION_SYMBOLS)
    if not DEFAULT_NSE_EQUITY_CALENDAR.is_trading_day(session):
        raise ValueError(f"{session.isoformat()} is not an NSE equity regular trading session")
    results = []
    completed = failed = 0
    for symbol in universe:
        try:
            result = run_dhan_paper_session(db, user_id, symbol, session.isoformat(), interval, finalize_validation=False)
            status = "COMPLETE" if result.get("validation", {}).get("status") == "COMPLETE" else "REJECTED"
            results.append({"symbol": symbol, "status": status, "result": result})
            if status == "COMPLETE":
                completed += 1
            else:
                failed += 1
        except Exception as exc:
            failed += 1
            results.append({"symbol": symbol, "status": "OPERATIONAL_FAILURE", "error_type": type(exc).__name__})
    run_key = validation_run_key(session)
    day = finalize_multi_symbol_validation_day(db, user_id, run_key, session, universe)
    manifest = persist_validation_manifest(db, user_id, run_key)
    return {
        "mode": "SIMULATION_ONLY", "session": session.isoformat(), "interval": interval,
        "validation_run": run_key, "universe": universe, "symbols_requested": len(universe),
        "completed_symbols": completed, "failed_symbols": failed, "day_status": day.status, "manifest_root_hash": manifest.root_hash,
        "results": results, "broker_orders_enabled": False,
        "calendar": {"market": DEFAULT_NSE_EQUITY_CALENDAR.market, "source": DEFAULT_NSE_EQUITY_CALENDAR.source, "source_version": DEFAULT_NSE_EQUITY_CALENDAR.source_version},
    }
