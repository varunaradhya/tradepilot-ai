from __future__ import annotations
import json
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.paper_trade import PaperTrade
from app.models.paper_validation_day import PaperValidationDay
from app.services.paper_reconciliation import reconcile_paper_state

VALIDATION_DAYS=30

def validation_run_key(start: date, days: int=VALIDATION_DAYS)->str:
    if days<1 or days>30: raise ValueError("validation window must be between 1 and 30 days")
    return f"P10_{start.isoformat()}_{days}D"

def record_validation_day(db: Session,user_id:int,run_key:str,session_date:date,status:str,trades:int,net_pnl:float,data_quality:dict)->PaperValidationDay:
    row=db.query(PaperValidationDay).filter(PaperValidationDay.user_id==user_id,PaperValidationDay.validation_run==run_key,PaperValidationDay.session_date==session_date).first()
    if row is None:
        row=PaperValidationDay(user_id=user_id,validation_run=run_key,session_date=session_date)
        db.add(row)
    row.status=status[:30]; row.trades=max(0,int(trades)); row.net_pnl=float(net_pnl); row.data_quality_json=json.dumps(data_quality,sort_keys=True)
    db.commit(); db.refresh(row); return row

def build_validation_report(db: Session,user_id:int,run_key:str)->dict:
    rows=db.query(PaperValidationDay).filter(PaperValidationDay.user_id==user_id,PaperValidationDay.validation_run==run_key).order_by(PaperValidationDay.session_date.asc()).all()
    trades=db.query(PaperTrade).filter(PaperTrade.user_id==user_id).all()
    total_pnl=sum(float(t.net_pnl or 0) for t in trades if str(t.status).upper()=="CLOSED")
    wins=sum(1 for t in trades if str(t.status).upper()=="CLOSED" and float(t.net_pnl or 0)>0)
    losses=sum(1 for t in trades if str(t.status).upper()=="CLOSED" and float(t.net_pnl or 0)<0)
    return {
        "validation_run":run_key,"window_days":30,"days_recorded":len(rows),
        "status":"EVIDENCE_PENDING" if len(rows)<30 else "COMPLETE",
        "evidence_is_descriptive":True,
        "live_execution_enabled":False,
        "days":[{"date":r.session_date,"status":r.status,"trades":r.trades,"net_pnl":r.net_pnl,"data_quality":json.loads(r.data_quality_json)} for r in rows],
        "aggregate":{"closed_trades":wins+losses,"wins":wins,"losses":losses,"net_pnl":total_pnl},
    }
