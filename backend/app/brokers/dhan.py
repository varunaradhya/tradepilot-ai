from typing import Any
import httpx
class DhanAPIError(Exception): pass
class DhanClient:
 BASE_URL="https://api.dhan.co/v2"
 def __init__(self,client_id:str,access_token:str): self.client_id=client_id; self.access_token=access_token
 def _request(self,method:str,path:str,json:dict[str,Any]|None=None)->Any:
  headers={"Accept":"application/json","Content-Type":"application/json","access-token":self.access_token,"client-id":self.client_id}
  try:r=httpx.request(method,f"{self.BASE_URL}{path}",headers=headers,json=json,timeout=30.0)
  except httpx.HTTPError as exc:raise DhanAPIError(f"Dhan connection failed: {exc}") from exc
  if r.status_code>=400:
   try:p=r.json()
   except Exception:p=r.text
   raise DhanAPIError(f"Dhan API returned {r.status_code}: {p}")
  try:return r.json()
  except Exception as exc:raise DhanAPIError("Dhan returned invalid JSON.") from exc
 def profile(self):return self._request("GET","/profile")
 def holdings(self):return self._request("GET","/holdings") or []
 def positions(self):return self._request("GET","/positions") or []
 def orders(self):return self._request("GET","/orders") or []
 def trades(self):return self._request("GET","/trades") or []
 def option_expiries(self,underlying_security_id:int,underlying_segment:str):return self._request("POST","/optionchain/expirylist",{"UnderlyingScrip":underlying_security_id,"UnderlyingSeg":underlying_segment})
 def option_chain(self,underlying_security_id:int,underlying_segment:str,expiry:str):return self._request("POST","/optionchain",{"UnderlyingScrip":underlying_security_id,"UnderlyingSeg":underlying_segment,"Expiry":expiry})
 def place_order(self,order:dict[str,Any]):return self._request("POST","/orders",order)
 def get_order(self,order_id:str):return self._request("GET",f"/orders/{order_id}")
 def cancel_order(self,order_id:str):return self._request("DELETE",f"/orders/{order_id}")
 def pnl_exit(self,profit_value:float,loss_value:float,product_types:list[str]|None=None,enable_kill_switch:bool=True):return self._request("POST","/pnlExit",{"profitValue":f"{profit_value:.2f}","lossValue":f"{loss_value:.2f}","productType":product_types or ["INTRADAY"],"enableKillSwitch":enable_kill_switch})
 def pnl_exit_status(self):return self._request("GET","/pnlExit")
 def activate_kill_switch(self):return self._request("POST","/killswitch?killSwitchStatus=ACTIVATE")
 def deactivate_kill_switch(self):return self._request("POST","/killswitch?killSwitchStatus=DEACTIVATE")
 def kill_switch_status(self):return self._request("GET","/killswitch")
 def historical_daily(self,security_id:str,exchange_segment:str,instrument:str,from_date:str,to_date:str,oi:bool=False,expiry_code:int=0):return self._request("POST","/charts/historical",{"securityId":security_id,"exchangeSegment":exchange_segment,"instrument":instrument,"expiryCode":expiry_code,"oi":oi,"fromDate":from_date,"toDate":to_date})
 def historical_intraday(self,security_id:str,exchange_segment:str,instrument:str,interval:str,from_date:str,to_date:str,oi:bool=False,expiry_code:int=0):return self._request("POST","/charts/intraday",{"securityId":security_id,"exchangeSegment":exchange_segment,"instrument":instrument,"interval":interval,"expiryCode":expiry_code,"oi":oi,"fromDate":from_date,"toDate":to_date})
 def rolling_option(self,security_id:str,expiry_flag:str,expiry_code:int,strike:str,option_type:str,from_date:str,to_date:str,interval:str="5"):
  return self._request("POST","/charts/rollingoption",{"exchangeSegment":"NSE_FNO","interval":interval,"securityId":security_id,"instrument":"OPTIDX","expiryFlag":expiry_flag,"expiryCode":expiry_code,"strike":strike,"drvOptionType":option_type,"requiredData":["open","high","low","close","iv","volume","strike","oi","spot"],"fromDate":from_date,"toDate":to_date})
