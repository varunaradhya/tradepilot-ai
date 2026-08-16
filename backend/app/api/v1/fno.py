from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from app.brokers.dhan import DhanAPIError,DhanClient
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.broker_service import get_access_token,get_user_broker
from app.services.fno_execution import execute_fno_decision
from app.services.fno_strategy import FNOConfig,build_fno_decision,select_option_contracts
from app.services.fno_instrument_service import fno_instrument_master
router=APIRouter(prefix="/fno",tags=["F&O"])
class OptionChainRequest(BaseModel): underlying_security_id:int=Field(gt=0); underlying_segment:str=Field(default="IDX_I",min_length=2,max_length=20); expiry:str=Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
class ExpiryRequest(BaseModel): underlying_security_id:int=Field(gt=0); underlying_segment:str=Field(default="IDX_I",min_length=2,max_length=20)
class FNODecisionRequest(BaseModel): underlying:dict[str,Any]; direction:str; option_chain:dict[str,Any]; config:dict[str,Any]={}
class FNOExecuteRequest(BaseModel): decision:dict[str,Any]; correlation_id:str=Field(default="tradepilot-fno",max_length=30)
def _dhan(db,user_id:int)->DhanClient:
 c=get_user_broker(db,user_id,"DHAN")
 if c is None:raise HTTPException(status_code=404,detail="Dhan is not connected.")
 return DhanClient(c.client_id,get_access_token(c))
@router.get("/underlyings")
def underlyings(q:str=Query(default="",max_length=50),current_user:User=Depends(get_current_user)):
 try:return [{"security_id":x.security_id,"exchange_segment":x.exchange_segment,"symbol":x.symbol,"name":x.name} for x in fno_instrument_master.search(q)]
 except Exception as exc:raise HTTPException(status_code=503,detail=f"Unable to load NSE F&O underlyings: {exc}") from exc
@router.post("/expiries")
def expiries(data:ExpiryRequest,current_user:User=Depends(get_current_user),db=Depends(get_db)):
 try:return _dhan(db,current_user.id).option_expiries(data.underlying_security_id,data.underlying_segment)
 except DhanAPIError as exc:raise HTTPException(status_code=502,detail=str(exc)) from exc
@router.post("/chain")
def option_chain(data:OptionChainRequest,current_user:User=Depends(get_current_user),db=Depends(get_db)):
 try:return _dhan(db,current_user.id).option_chain(data.underlying_security_id,data.underlying_segment,data.expiry)
 except DhanAPIError as exc:raise HTTPException(status_code=502,detail=str(exc)) from exc
@router.post("/scan")
def scan(data:FNODecisionRequest,current_user:User=Depends(get_current_user)):
 try:cfg=FNOConfig(**{k:v for k,v in data.config.items() if k in FNOConfig.__dataclass_fields__})
 except (TypeError,ValueError) as exc:raise HTTPException(status_code=422,detail=str(exc)) from exc
 candidates=select_option_contracts(data.option_chain,data.direction,cfg)
 return {"candidates":candidates,"decision":build_fno_decision(data.underlying,data.direction,candidates,cfg),"mode":"PAPER_ONLY"}
@router.post("/execute")
def execute(data:FNOExecuteRequest,current_user:User=Depends(get_current_user),db=Depends(get_db)):
 try:return execute_fno_decision(_dhan(db,current_user.id),data.decision,data.correlation_id)
 except (DhanAPIError,ValueError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
