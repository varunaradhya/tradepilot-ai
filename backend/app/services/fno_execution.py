from __future__ import annotations
from typing import Any
from app.brokers.dhan import DhanClient
from app.core.config import TRADEPILOT_LIVE_EXECUTION_ENABLED

def validate_fno_order(decision:dict[str,Any])->dict[str,Any]:
    if decision.get("decision")!="QUALIFIED": raise ValueError("Only QUALIFIED decisions can reach execution.")
    c=decision.get("contract") or {}; sid=c.get("security_id"); qty=int(decision.get("quantity") or 0); lot=max(1,int(decision.get("lot_size") or 1))
    if not sid or qty<=0: raise ValueError("Qualified decision has invalid contract or quantity.")
    if qty%lot: raise ValueError("Quantity must be lot-size aligned.")
    return {"security_id":str(sid),"quantity":qty,"entry":float(decision["entry"]),"stop":float(decision["stop"]),"target":float(decision["target"]),"side":"BUY"}

def execute_fno_decision(client:DhanClient,decision:dict[str,Any],correlation_id:str)->dict[str,Any]:
    order=validate_fno_order(decision)
    if not TRADEPILOT_LIVE_EXECUTION_ENABLED:return {"mode":"PAPER_ONLY","submitted":False,"reason":"LIVE_EXECUTION_DISABLED","order":order}
    payload={"dhanClientId":client.client_id,"correlationId":correlation_id[:30],"transactionType":"BUY","exchangeSegment":"NSE_FNO","productType":"INTRADAY","orderType":"MARKET","validity":"DAY","securityId":order["security_id"],"quantity":order["quantity"],"disclosedQuantity":"","price":"","triggerPrice":"","afterMarketOrder":False,"amoTime":"","boProfitValue":"","boStopLossValue":""}
    return {"mode":"LIVE","submitted":True,"order":client.place_order(payload)}
