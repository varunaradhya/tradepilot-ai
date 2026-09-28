from __future__ import annotations
from datetime import date
from typing import Iterable
from app.services.paper_dhan_service import run_dhan_paper_session

def run_daily_dhan_validation(db, user_id:int, symbols:Iterable[str], session:date, interval:str="5")->dict:
    results=[]; completed=0; failed=0
    for symbol in dict.fromkeys(s.strip().upper() for s in symbols if s and s.strip()):
        try:
            result=run_dhan_paper_session(db,user_id,symbol,session.isoformat(),interval)
            results.append({"symbol":symbol,"status":"COMPLETE" if result.get("validation",{}).get("status")=="COMPLETE" else "REJECTED","result":result})
            if result.get("validation",{}).get("status")=="COMPLETE": completed+=1
            else: failed+=1
        except Exception as exc:
            failed+=1
            results.append({"symbol":symbol,"status":"OPERATIONAL_FAILURE","error_type":type(exc).__name__})
    return {"mode":"SIMULATION_ONLY","session":session.isoformat(),"interval":interval,"symbols_requested":len(results),"completed":completed,"failed":failed,"results":results,"broker_orders_enabled":False}
