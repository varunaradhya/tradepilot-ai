from __future__ import annotations
import hashlib,json
from datetime import date,datetime,timezone
from sqlalchemy.orm import Session
from app.models.paper_trade import PaperTrade
from app.models.paper_validation_day import PaperValidationDay
VALIDATION_DAYS=30
VALID_STATUSES={"VALID","DATA_QUALITY_FAILED","OPERATIONAL_FAILURE","NO_DATA"}

def validation_run_key(start:date,days:int=VALIDATION_DAYS)->str:
    if days<1 or days>30: raise ValueError("validation window must be between 1 and 30 days")
    return f"P10_{start.isoformat()}_{days}D"

def _fingerprint(row:PaperValidationDay)->str:
    payload={"run":row.validation_run,"date":row.session_date.isoformat(),"status":row.status,"trades":row.trades,"net_pnl":row.net_pnl,"quality":json.loads(row.data_quality_json)}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def record_validation_day(db:Session,user_id:int,run_key:str,session_date:date,status:str,trades:int,net_pnl:float,data_quality:dict)->PaperValidationDay:
    status=status.upper()
    if status not in VALID_STATUSES: raise ValueError("invalid validation status")
    row=db.query(PaperValidationDay).filter(PaperValidationDay.user_id==user_id,PaperValidationDay.validation_run==run_key,PaperValidationDay.session_date==session_date).first()
    if row is not None and row.status=="COMPLETE":
        return row
    if row is None:
        row=PaperValidationDay(user_id=user_id,validation_run=run_key,session_date=session_date)
        db.add(row)
    row.status=status[:30]; row.trades=max(0,int(trades)); row.net_pnl=float(net_pnl); row.data_quality_json=json.dumps(data_quality,sort_keys=True)
    db.commit(); db.refresh(row); return row

def complete_validation_day(db:Session,user_id:int,run_key:str,session_date:date,trades:int,net_pnl:float,data_quality:dict)->PaperValidationDay:
    row=record_validation_day(db,user_id,run_key,session_date,"VALID",trades,net_pnl,data_quality)
    row.status="COMPLETE"; db.commit(); db.refresh(row); return row

def capture_day_from_ledger(db:Session,user_id:int,run_key:str,session_date:date,data_quality:dict)->PaperValidationDay:
    trades=db.query(PaperTrade).filter(PaperTrade.user_id==user_id).all()
    day_trades=[t for t in trades if t.created_at and t.created_at.astimezone(timezone.utc).date()==session_date]
    closed=[t for t in day_trades if str(t.status).upper()=="CLOSED"]
    status="VALID" if data_quality.get("valid",False) else "DATA_QUALITY_FAILED"
    if not day_trades and status=="VALID": status="NO_DATA"
    return record_validation_day(db,user_id,run_key,session_date,status,len(closed),sum(float(t.pnl or 0) for t in closed),data_quality)

def build_validation_report(db:Session,user_id:int,run_key:str)->dict:
    rows=db.query(PaperValidationDay).filter(PaperValidationDay.user_id==user_id,PaperValidationDay.validation_run==run_key).order_by(PaperValidationDay.session_date.asc()).all()
    valid=sum(1 for r in rows if r.status=="COMPLETE")
    closed=db.query(PaperTrade).filter(PaperTrade.user_id==user_id).all()
    closed=[t for t in closed if str(t.status).upper()=="CLOSED"]
    total_pnl=sum(float(t.pnl or 0) for t in closed); wins=sum(1 for t in closed if float(t.pnl or 0)>0); losses=sum(1 for t in closed if float(t.pnl or 0)<0)
    status="COMPLETE" if valid>=30 else ("DATA_QUALITY_FAILED" if any(r.status=="DATA_QUALITY_FAILED" for r in rows) else "EVIDENCE_PENDING")
    return {"validation_run":run_key,"window_days":30,"days_recorded":len(rows),"complete_days":valid,"status":status,"evidence_is_descriptive":True,"live_execution_enabled":False,"days":[{"date":r.session_date,"status":r.status,"trades":r.trades,"net_pnl":r.net_pnl,"data_quality":json.loads(r.data_quality_json),"fingerprint":_fingerprint(r)} for r in rows],"aggregate":{"closed_trades":len(closed),"wins":wins,"losses":losses,"net_pnl":total_pnl}}
