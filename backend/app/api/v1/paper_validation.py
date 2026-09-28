from datetime import date
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.paper_validation_job import run_daily_dhan_validation
from app.services.paper_validation_service import (
    DEFAULT_VALIDATION_SYMBOLS, validation_run_key, build_validation_report,
    capture_day_from_ledger, complete_validation_day, validation_progress, build_validation_manifest, persist_validation_manifest, verify_validation_manifest,
)
from app.services.nse_equity_calendar import DEFAULT_NSE_EQUITY_CALENDAR, nse_equity_holidays

router = APIRouter(prefix="/paper-validation", tags=["Paper Validation"])

class ValidationCaptureRequest(BaseModel):
    start: date
    session_date: date
    valid_data: bool = True
    bars: int = Field(default=0, ge=0)
    duplicate_timestamps: int = Field(default=0, ge=0)
    invalid_ohlc: int = Field(default=0, ge=0)
    stale_bars: int = Field(default=0, ge=0)
    provider_errors: int = Field(default=0, ge=0)

class MultiSymbolValidationRequest(BaseModel):
    session_date: date
    symbols: list[str] = Field(default_factory=lambda: list(DEFAULT_VALIDATION_SYMBOLS))
    interval: str = "5"

@router.get("/calendar")
def validation_calendar() -> dict[str, Any]:
    return {"mode": "SIMULATION_ONLY", "market": DEFAULT_NSE_EQUITY_CALENDAR.market, "source": DEFAULT_NSE_EQUITY_CALENDAR.source, "source_version": DEFAULT_NSE_EQUITY_CALENDAR.source_version, "year": DEFAULT_NSE_EQUITY_CALENDAR.calendar_year, "holidays": sorted(day.isoformat() for day in nse_equity_holidays(DEFAULT_NSE_EQUITY_CALENDAR.calendar_year))}

@router.get("/universe")
def validation_universe() -> dict[str, Any]:
    return {"mode": "SIMULATION_ONLY", "symbols": list(DEFAULT_VALIDATION_SYMBOLS), "min_symbols": 3, "max_symbols": 10, "market": "NSE_EQ"}

@router.get("/report")
def validation_report(start: date, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        key = validation_run_key(start)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return build_validation_report(db, current_user.id, key)

@router.post("/capture")
def capture_day(payload: ValidationCaptureRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        key = validation_run_key(payload.start)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    quality = {"valid": payload.valid_data, "bars": payload.bars, "duplicate_timestamps": payload.duplicate_timestamps, "invalid_ohlc": payload.invalid_ohlc, "stale_bars": payload.stale_bars, "provider_errors": payload.provider_errors}
    row = capture_day_from_ledger(db, current_user.id, key, payload.session_date, quality)
    report = build_validation_report(db, current_user.id, key)
    latest = report["days"][-1] if report["days"] else {}
    return {"mode": "SIMULATION_ONLY", "status": row.status, "validation_run": key, "session_date": row.session_date, "fingerprint": latest.get("fingerprint")}

@router.post("/complete")
def complete_day(payload: ValidationCaptureRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    if not payload.valid_data or any([payload.duplicate_timestamps, payload.invalid_ohlc, payload.stale_bars, payload.provider_errors]):
        raise HTTPException(409, "Day cannot be completed while data-quality or provider failures are present")
    try:
        key = validation_run_key(payload.start)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    row = complete_validation_day(db, current_user.id, key, payload.session_date, {"valid": True, "bars": payload.bars})
    report = build_validation_report(db, current_user.id, key)
    latest = report["days"][-1] if report["days"] else {}
    return {"mode": "SIMULATION_ONLY", "status": row.status, "validation_run": key, "report_status": report["status"], "fingerprint": latest.get("fingerprint")}

@router.get("/manifest")
def validation_manifest(start: date, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        key = validation_run_key(start)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return persist_validation_manifest(db, current_user.id, key).manifest_json and build_validation_manifest(db, current_user.id, key)

@router.get("/manifest/verify")
def verify_manifest(start: date, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        key = validation_run_key(start)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return verify_validation_manifest(db, current_user.id, key)

@router.get("/progress")
def validation_progress_report(start: date, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        key = validation_run_key(start)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"mode": "SIMULATION_ONLY", "validation_run": key, **validation_progress(db, current_user.id, key, start)}

@router.post("/daily-dhan")
def daily_dhan_validation(payload: MultiSymbolValidationRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        return run_daily_dhan_validation(db, current_user.id, payload.symbols, payload.session_date, payload.interval)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
