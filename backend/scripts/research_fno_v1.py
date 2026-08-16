from __future__ import annotations
import argparse,json,os
from datetime import date
from pathlib import Path
from app.brokers.dhan import DhanClient
from app.services.fno_research_pipeline import chunk_date_range,run_v1_backtest,validate_bars
from app.services.fno_strategy_v1 import FNOORBConfig
from app.services.fno_validation import ValidationGate,evaluate_backtest

def normalize(payload):
    if isinstance(payload,dict) and isinstance(payload.get("data"),dict):payload=payload["data"]
    if not isinstance(payload,dict):return []
    keys={k:payload.get(k,[]) for k in ("open","high","low","close","volume","timestamp","open_interest")};n=max((len(v) for v in keys.values() if isinstance(v,list)),default=0);rows=[]
    for i in range(n):
        if any(i>=len(keys[k]) for k in ("open","high","low","close","timestamp")):continue
        rows.append({"open":keys["open"][i],"high":keys["high"][i],"low":keys["low"][i],"close":keys["close"][i],"volume":keys["volume"][i] if i<len(keys["volume"]) else 0,"timestamp":keys["timestamp"][i]})
    return rows

def main():
    p=argparse.ArgumentParser(description="Run frozen F&O V1 research against Dhan historical data.")
    p.add_argument("--security-id",default="13");p.add_argument("--instrument",default="FUTIDX");p.add_argument("--exchange",default="NSE_FNO");p.add_argument("--from-date",required=True);p.add_argument("--to-date",required=True);p.add_argument("--expiry-code",type=int,default=0);p.add_argument("--out",default="data/research/fno_v1.json");a=p.parse_args()
    cid=os.environ.get("DHAN_CLIENT_ID");token=os.environ.get("DHAN_ACCESS_TOKEN")
    if not cid or not token:raise SystemExit("Set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN before running research.")
    start=date.fromisoformat(a.from_date);end=date.fromisoformat(a.to_date)
    if start>=end:raise SystemExit("from-date must be earlier than to-date")
    client=DhanClient(cid,token);rows=[]
    for w in chunk_date_range(start,end,90):
        payload=client.historical_intraday(a.security_id,a.exchange,a.instrument,"5",f"{w.start} 09:15:00",f"{w.end} 15:30:00",oi=True,expiry_code=a.expiry_code)
        rows.extend(normalize(payload))
    rows.sort(key=lambda x:x["timestamp"]);quality=validate_bars(rows)
    if not quality["quality_ok"]:raise SystemExit(f"Historical data quality gate failed: {quality}")
    result=run_v1_backtest(rows,FNOORBConfig());result["data_quality"]=quality;result["data_coverage"]={"from":a.from_date,"to":a.to_date,"bars":len(rows),"instrument":a.instrument,"exchange":a.exchange,"expiry_code":a.expiry_code,"source":"Dhan historical API"}
    yearly={}
    for t in result["trades_detail"]:yearly[t["date"][:4]]=yearly.get(t["date"][:4],0)+t["pnl"]
    result["yearly_pnl"]=yearly;result["promotion_screen"]=evaluate_backtest(result,yearly,ValidationGate())
    Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({"coverage":result["data_coverage"],"data_quality":quality,"metrics":{k:result[k] for k in ("trades","return_percent","profit_factor","expectancy_per_trade","max_drawdown_percent","win_rate_percent")},"yearly_pnl":yearly,"promotion_screen":result["promotion_screen"]},indent=2))
if __name__=="__main__":main()
