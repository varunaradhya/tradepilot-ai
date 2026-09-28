from datetime import date
from typing import Any
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.paper_validation_service import validation_run_key,build_validation_report,capture_day_from_ledger,complete_validation_day

router=APIRouter(prefix="/paper-validation",tags=["Paper Validation"])

class ValidationCaptureRequest(BaseModel):
    start: date
    session_date: date
    valid_data: bool=True
    bars: int=Field(default=0,ge=0)
    duplicate_timestamps: int=Field(default=0,ge=0)
    invalid_ohlc: int=Field(default=0,ge=0)
    stale_bars: int=Field(default=0,ge=0)
    provider_errors: int=Field(default=0,ge=0)

@router.get("/report")
def validation_report(start:date,current_user:User=Depends(get_current_user),db:Session=Depends(get_db))->dict[str,Any]:
    try:key=validation_run_key(start)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    return build_validation_report(db,current_user.id,key)

@router.post("/capture")
def capture_day(payload:ValidationCaptureRequest,current_user:User=Depends(get_current_user),db:Session=Depends(get_db))->dict[str,Any]:
    try:key=validation_run_key(payload.start)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    quality={"valid":payload.valid_data,"bars":payload.bars,"duplicate_timestamps":payload.duplicate_timestamps,"invalid_ohlc":payload.invalid_ohlc,"stale_bars":payload.stale_bars,"provider_errors":payload.provider_errors}
    row=capture_day_from_ledger(db,current_user.id,key,payload.session_date,quality)
    return {"mode":"SIMULATION_ONLY","status":row.status,"validation_run":key,"session_date":row.session_date,"fingerprint":build_validation_report(db,current_user.id,key)["days"][-1]["fingerprint"]}

@router.post("/complete")
def complete_day(payload:ValidationCaptureRequest,current_user:User=Depends(get_current_user),db:Session=Depends(get_db))->dict[str,Any]:
    if not payload.valid_data or any([payload.duplicate_timestamps,payload.invalid_ohlc,payload.stale_bars,payload.provider_errors]):
        raise HTTPException(409,"Day cannot be completed while data-quality or provider failures are present")
    try:key=validation_run_key(payload.start)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    row=complete_validation_day(db,current_user.id,key,payload.session_date,{"valid":True,"bars":payload.bars})
    report=build_validation_report(db,current_user.id,key)
    return {"mode":"SIMULATION_ONLY","status":row.status,"validation_run":key,"report_status":report["status"],"fingerprint":report["days"][-1]["fingerprint"]}
