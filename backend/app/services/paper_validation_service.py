from __future__ import annotations
import hashlib, json
from datetime import date, datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from app.models.paper_trade import PaperTrade
from app.models.paper_validation_day import PaperValidationDay
from app.models.paper_validation_symbol import PaperValidationSymbol
from app.models.paper_validation_manifest import PaperValidationManifest
from app.services.nse_equity_calendar import DEFAULT_NSE_EQUITY_CALENDAR, NSEEquityCalendar

VALIDATION_DAYS = 30
VALID_STATUSES = {"VALID", "DATA_QUALITY_FAILED", "OPERATIONAL_FAILURE", "NO_DATA"}
IST = ZoneInfo("Asia/Kolkata")
DEFAULT_VALIDATION_SYMBOLS = ("RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK")
MIN_VALIDATION_SYMBOLS = 3
MAX_VALIDATION_SYMBOLS = 10

def validation_run_key(start: date, days: int = VALIDATION_DAYS) -> str:
    if days < 1 or days > 30:
        raise ValueError("validation window must be between 1 and 30 days")
    return f"P10_{start.isoformat()}_{days}D"

def normalize_validation_symbols(symbols) -> list[str]:
    normalized = []
    for symbol in symbols or ():
        value = str(symbol).strip().upper().removesuffix(".NS").removesuffix(".BO")
        if value and value not in normalized:
            normalized.append(value)
    if not MIN_VALIDATION_SYMBOLS <= len(normalized) <= MAX_VALIDATION_SYMBOLS:
        raise ValueError(f"validation universe must contain {MIN_VALIDATION_SYMBOLS} to {MAX_VALIDATION_SYMBOLS} unique symbols")
    return normalized

def _fingerprint(row: PaperValidationDay) -> str:
    payload = {"run": row.validation_run, "date": row.session_date.isoformat(), "status": row.status, "trades": row.trades, "net_pnl": row.net_pnl, "quality": json.loads(row.data_quality_json)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def _symbol_fingerprint(row: PaperValidationSymbol) -> str:
    payload = {"run": row.validation_run, "date": row.session_date.isoformat(), "symbol": row.symbol, "status": row.status, "bars": row.bars, "trades": row.trades, "net_pnl": row.net_pnl, "quality": json.loads(row.data_quality_json)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def record_validation_symbol(db: Session, user_id: int, run_key: str, session_date: date, symbol: str, status: str, bars: int, trades: int, net_pnl: float, data_quality: dict, *, commit: bool = True) -> PaperValidationSymbol:
    status = status.upper()
    if status not in VALID_STATUSES:
        raise ValueError("invalid validation status")
    symbol = str(symbol).strip().upper()
    row = db.query(PaperValidationSymbol).filter(
        PaperValidationSymbol.user_id == user_id,
        PaperValidationSymbol.validation_run == run_key,
        PaperValidationSymbol.session_date == session_date,
        PaperValidationSymbol.symbol == symbol,
    ).first()
    if row is not None and row.status == "COMPLETE":
        return row
    if row is None:
        row = PaperValidationSymbol(user_id=user_id, validation_run=run_key, session_date=session_date, symbol=symbol)
        db.add(row)
    row.status = status[:30]
    row.bars = max(0, int(bars))
    row.trades = max(0, int(trades))
    row.net_pnl = float(net_pnl)
    row.data_quality_json = json.dumps(data_quality, sort_keys=True)
    if commit:
        db.commit()
    db.refresh(row)
    return row

def _aggregate_symbol_rows(db: Session, user_id: int, run_key: str, session_date: date, expected_symbols=None) -> tuple[str, int, float, dict]:
    rows = db.query(PaperValidationSymbol).filter(
        PaperValidationSymbol.user_id == user_id,
        PaperValidationSymbol.validation_run == run_key,
        PaperValidationSymbol.session_date == session_date,
    ).all()
    expected = normalize_validation_symbols(expected_symbols) if expected_symbols is not None else sorted({r.symbol for r in rows})
    by_symbol = {r.symbol: r for r in rows}
    missing = [s for s in expected if s not in by_symbol]
    failed = [s for s in expected if by_symbol[s].status != "COMPLETE"] if not missing else [s for s in expected if s in by_symbol and by_symbol[s].status != "COMPLETE"]
    quality = {
        "valid": not missing and not failed and bool(expected),
        "expected_symbols": expected,
        "covered_symbols": sorted(by_symbol),
        "missing_symbols": missing,
        "failed_symbols": failed,
        "symbol_count": len(expected),
        "bars": sum(r.bars for r in rows if r.symbol in expected),
    }
    if missing:
        return "NO_DATA", 0, 0.0, quality
    if failed:
        return "DATA_QUALITY_FAILED", sum(r.trades for r in rows if r.symbol in expected), sum(float(r.net_pnl) for r in rows if r.symbol in expected), quality
    return "VALID", sum(r.trades for r in rows if r.symbol in expected), sum(float(r.net_pnl) for r in rows if r.symbol in expected), quality

def finalize_multi_symbol_validation_day(db: Session, user_id: int, run_key: str, session_date: date, expected_symbols) -> PaperValidationDay:
    status, trades, pnl, quality = _aggregate_symbol_rows(db, user_id, run_key, session_date, expected_symbols)
    if status != "VALID":
        return record_validation_day(db, user_id, run_key, session_date, status, trades, pnl, quality)
    row = record_validation_day(db, user_id, run_key, session_date, "VALID", trades, pnl, quality)
    row.status = "COMPLETE"
    db.commit()
    db.refresh(row)
    return row

def record_validation_day(db: Session, user_id: int, run_key: str, session_date: date, status: str, trades: int, net_pnl: float, data_quality: dict, *, commit: bool = True) -> PaperValidationDay:
    status = status.upper()
    if status not in VALID_STATUSES:
        raise ValueError("invalid validation status")
    row = db.query(PaperValidationDay).filter(PaperValidationDay.user_id == user_id, PaperValidationDay.validation_run == run_key, PaperValidationDay.session_date == session_date).first()
    if row is not None and row.status == "COMPLETE":
        return row
    if row is None:
        row = PaperValidationDay(user_id=user_id, validation_run=run_key, session_date=session_date)
        db.add(row)
    row.status = status[:30]
    row.trades = max(0, int(trades))
    row.net_pnl = float(net_pnl)
    row.data_quality_json = json.dumps(data_quality, sort_keys=True)
    if commit:
        db.commit()
    db.refresh(row)
    return row

def complete_validation_day(db: Session, user_id: int, run_key: str, session_date: date, data_quality: dict, *, commit: bool = True) -> PaperValidationDay:
    row = capture_day_from_ledger(db, user_id, run_key, session_date, data_quality, commit=commit)
    if row.status != "VALID":
        raise ValueError("validation day is not valid")
    row.status = "COMPLETE"
    if commit:
        db.commit()
    db.refresh(row)
    return row

def capture_day_from_ledger(db: Session, user_id: int, run_key: str, session_date: date, data_quality: dict, *, commit: bool = True) -> PaperValidationDay:
    status = "VALID" if data_quality.get("valid", False) else "DATA_QUALITY_FAILED"
    # A valid market session with zero strategy trades is valid evidence; NO_DATA means no bars.
    bars = int(data_quality.get("bars") or 0)
    if bars <= 0 and status == "VALID":
        status = "NO_DATA"
    trades = db.query(PaperTrade).filter(PaperTrade.user_id == user_id).all()
    day_trades = [t for t in trades if t.created_at and t.created_at.astimezone(IST).date() == session_date]
    closed = [t for t in day_trades if str(t.status).upper() == "CLOSED"]
    return record_validation_day(db, user_id, run_key, session_date, status, len(closed), sum(float(t.pnl or 0) for t in closed), data_quality, commit=commit)

def expected_trading_days(start: date, end: date, holidays=frozenset(), calendar: NSEEquityCalendar = DEFAULT_NSE_EQUITY_CALENDAR) -> list[date]:
    if end < start:
        raise ValueError("end must not be before start")
    if holidays:
        allowed = set(calendar.holidays) | set(holidays)
        custom = NSEEquityCalendar(
            market=calendar.market,
            calendar_year=calendar.calendar_year,
            source=calendar.source,
            source_version=calendar.source_version,
            holidays=frozenset(allowed),
        )
    else:
        custom = calendar
    sessions = custom.expected_sessions(start, VALIDATION_DAYS)
    return [day for day in sessions if day <= end]

def validation_progress(db: Session, user_id: int, run_key: str, start: date, holidays=frozenset(), calendar: NSEEquityCalendar = DEFAULT_NSE_EQUITY_CALENDAR) -> dict:
    expected = expected_trading_days(start, start + timedelta(days=44), holidays, calendar)[:VALIDATION_DAYS]
    rows = db.query(PaperValidationDay).filter(PaperValidationDay.user_id == user_id, PaperValidationDay.validation_run == run_key).all()
    by_date = {row.session_date: row for row in rows}
    complete_dates = [d for d in expected if by_date.get(d) and by_date[d].status == "COMPLETE"]
    failed_dates = [d for d in expected if by_date.get(d) and by_date[d].status in {"DATA_QUALITY_FAILED", "OPERATIONAL_FAILURE", "NO_DATA"}]
    return {"required_sessions": VALIDATION_DAYS, "expected_sessions": len(expected), "completed_sessions": len(complete_dates), "failed_sessions": len(failed_dates), "remaining_sessions": max(VALIDATION_DAYS-len(complete_dates), 0), "complete": len(complete_dates) >= VALIDATION_DAYS, "evidence_is_descriptive": True, "calendar": {"market": calendar.market, "source": calendar.source, "source_version": calendar.source_version}, "expected_dates": [d.isoformat() for d in expected], "missing_dates": [d.isoformat() for d in expected if d not in by_date], "failed_dates": [d.isoformat() for d in failed_dates]}

def _canonical_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

def build_validation_manifest(db: Session, user_id: int, run_key: str) -> dict:
    rows = db.query(PaperValidationDay).filter(
        PaperValidationDay.user_id == user_id,
        PaperValidationDay.validation_run == run_key,
    ).order_by(PaperValidationDay.session_date.asc()).all()
    symbols = db.query(PaperValidationSymbol).filter(
        PaperValidationSymbol.user_id == user_id,
        PaperValidationSymbol.validation_run == run_key,
    ).order_by(PaperValidationSymbol.session_date.asc(), PaperValidationSymbol.symbol.asc()).all()
    previous = ""
    chain = []
    for day in rows:
        symbol_hashes = [_symbol_fingerprint(r) for r in symbols if r.session_date == day.session_date]
        day_payload = {
            "validation_run": run_key,
            "session_date": day.session_date.isoformat(),
            "day_fingerprint": _fingerprint(day),
            "symbol_fingerprints": symbol_hashes,
            "previous_hash": previous,
        }
        current = _canonical_hash(day_payload)
        chain.append({**day_payload, "chain_hash": current})
        previous = current
    report = build_validation_report(db, user_id, run_key)
    manifest = {
        "validation_run": run_key,
        "schema_version": "P10.7",
        "calendar": report["progress"]["calendar"],
        "symbols": report["symbols"],
        "required_sessions": VALIDATION_DAYS,
        "completed_sessions": report["progress"]["completed_sessions"],
        "days": chain,
        "evidence_is_descriptive": True,
        "live_execution_enabled": False,
    }
    root_hash = _canonical_hash(manifest)
    manifest["root_hash"] = root_hash
    return manifest

def persist_validation_manifest(db: Session, user_id: int, run_key: str) -> PaperValidationManifest:
    manifest = build_validation_manifest(db, user_id, run_key)
    row = db.query(PaperValidationManifest).filter(
        PaperValidationManifest.user_id == user_id,
        PaperValidationManifest.validation_run == run_key,
    ).first()
    if row is None:
        row = PaperValidationManifest(user_id=user_id, validation_run=run_key)
        db.add(row)
    row.status = "COMPLETE" if manifest["completed_sessions"] >= VALIDATION_DAYS else "PENDING"
    row.manifest_json = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    row.root_hash = manifest["root_hash"]
    db.commit()
    db.refresh(row)
    return row

def verify_validation_manifest(db: Session, user_id: int, run_key: str) -> dict:
    row = db.query(PaperValidationManifest).filter(
        PaperValidationManifest.user_id == user_id,
        PaperValidationManifest.validation_run == run_key,
    ).first()
    if row is None:
        return {"exists": False, "valid": False, "validation_run": run_key}
    current = build_validation_manifest(db, user_id, run_key)
    return {
        "exists": True,
        "valid": current["root_hash"] == row.root_hash,
        "validation_run": run_key,
        "stored_root_hash": row.root_hash,
        "current_root_hash": current["root_hash"],
        "status": row.status,
        "evidence_is_descriptive": True,
        "live_execution_enabled": False,
    }

def build_validation_report(db: Session, user_id: int, run_key: str) -> dict:
    rows = db.query(PaperValidationDay).filter(PaperValidationDay.user_id == user_id, PaperValidationDay.validation_run == run_key).order_by(PaperValidationDay.session_date.asc()).all()
    start = date.fromisoformat(run_key.split("_")[1])
    progress = validation_progress(db, user_id, run_key, start)
    symbols = db.query(PaperValidationSymbol).filter(PaperValidationSymbol.user_id == user_id, PaperValidationSymbol.validation_run == run_key).order_by(PaperValidationSymbol.session_date.asc(), PaperValidationSymbol.symbol.asc()).all()
    by_date = {}
    for row in symbols:
        by_date.setdefault(row.session_date, []).append(row)
    status = "COMPLETE" if progress["complete"] else ("DATA_QUALITY_FAILED" if any(r.status == "DATA_QUALITY_FAILED" for r in rows) else "EVIDENCE_PENDING")
    return {
        "validation_run": run_key, "window_days": VALIDATION_DAYS, "days_recorded": len(rows), "complete_days": sum(1 for r in rows if r.status == "COMPLETE"),
        "progress": progress, "status": status, "evidence_is_descriptive": True, "live_execution_enabled": False,
        "symbols": sorted({r.symbol for r in symbols}),
        "symbol_evidence": [{
            "date": r.session_date, "symbol": r.symbol, "status": r.status, "bars": r.bars, "trades": r.trades, "net_pnl": r.net_pnl,
            "data_quality": json.loads(r.data_quality_json), "fingerprint": _symbol_fingerprint(r)
        } for r in symbols],
        "cross_symbol": [{
            "date": d, "covered_symbols": sorted(r.symbol for r in rs), "complete_symbols": sorted(r.symbol for r in rs if r.status == "COMPLETE"),
            "failed_symbols": sorted(r.symbol for r in rs if r.status != "COMPLETE"), "net_pnl": sum(float(r.net_pnl) for r in rs), "trades": sum(r.trades for r in rs)
        } for d, rs in sorted(by_date.items())],
        "days": [{"date": r.session_date, "status": r.status, "trades": r.trades, "net_pnl": r.net_pnl, "data_quality": json.loads(r.data_quality_json), "fingerprint": _fingerprint(r)} for r in rows],
        "aggregate": {
            "closed_trades": sum(r.trades for r in rows if r.status == "COMPLETE"),
            "wins": None, "losses": None,
            "net_pnl": sum(float(r.net_pnl) for r in rows if r.status == "COMPLETE"),
        },
    }
