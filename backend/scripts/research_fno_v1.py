from __future__ import annotations
import argparse,json,os,sys
from datetime import date
from pathlib import Path
BACKEND_DIR=Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:sys.path.insert(0,str(BACKEND_DIR))
from app.brokers.dhan import DhanClient
from app.services.fno_research_pipeline import chunk_date_range,run_v1_backtest,validate_bars
from app.services.fno_strategy_v1 import FNOORBConfig
from app.services.fno_validation import ValidationGate,evaluate_backtest

def normalize(payload):
    if isinstance(payload,dict) and isinstance(payload.get("data"),dict):payload=payload["data"]
    if not isinstance(payload,dict):return []
    keys={k:payload.get(k,[]) for k in ("open","high","low","close","volume","timestamp")};n=max((len(v) for v in keys.values() if isinstance(v,list)),default=0);rows=[]
    for i in range(n):
        if any(i>=len(keys[k]) for k in ("open","high","low","close","timestamp")):continue
        rows.append({"open":keys["open"][i],"high":keys["high"][i],"low":keys["low"][i],"close":keys["close"][i],"volume":keys["volume"][i] if i<len(keys["volume"]) else 0,"timestamp":keys["timestamp"][i]})
    return rows

def dedupe_timestamp(rows):
    seen=set();out=[]
    for row in sorted(rows,key=lambda x:x.get("timestamp",0)):
        ts=row.get("timestamp")
        if ts in seen:continue
        seen.add(ts);out.append(row)
    return out,len(rows)-len(out)

def main():
    p=argparse.ArgumentParser(description="Run frozen F&O V1 research against Dhan historical NIFTY index data.")
    p.add_argument("--security-id",default="13");p.add_argument("--instrument",default="INDEX");p.add_argument("--exchange",default="IDX_I");p.add_argument("--from-date",required=True);p.add_argument("--to-date",required=True);p.add_argument("--expiry-code",type=int,default=0);p.add_argument("--out",default="data/research/fno_v1.json");a=p.parse_args()
    cid=os.environ.get("DHAN_CLIENT_ID");token=os.environ.get("DHAN_ACCESS_TOKEN")
    if not cid or not token:raise SystemExit("Set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN before running research.")
    start=date.fromisoformat(a.from_date);end=date.fromisoformat(a.to_date)
    if start>=end:raise SystemExit("from-date must be earlier than to-date")
    client=DhanClient(cid,token);rows=[];windows=chunk_date_range(start,end,90)
    print(f"Downloading {len(windows)} historical windows: {a.from_date} -> {a.to_date} ({a.exchange}/{a.instrument}/{a.security_id})")
    for n,w in enumerate(windows,1):
        print(f"[{n}/{len(windows)}] {w.start} -> {w.end}")
        payload=client.historical_intraday(a.security_id,a.exchange,a.instrument,"5",w.start.isoformat(),w.end.isoformat(),oi=False,expiry_code=a.expiry_code)
        chunk=normalize(payload);rows.extend(chunk);print(f"  received {len(chunk)} bars")
    raw_bars=len(rows);rows,removed=dedupe_timestamp(rows);print(f"Chunk overlap cleanup: removed {removed} duplicate boundary bars; usable bars={len(rows)}")
    quality=validate_bars(rows)
    if not quality["quality_ok"]:raise SystemExit(f"Historical data quality gate failed: {quality}")
    result=run_v1_backtest(rows,FNOORBConfig());result["data_quality"]=quality;result["data_coverage"]={"from":a.from_date,"to":a.to_date,"raw_bars":raw_bars,"bars":len(rows),"overlap_duplicates_removed":removed,"instrument":a.instrument,"exchange":a.exchange,"security_id":a.security_id,"source":"Dhan historical API"}
    yearly={}
    for t in result["trades_detail"]:yearly[t["date"][:4]]=yearly.get(t["date"][:4],0)+t["pnl"]
    result["yearly_pnl"]=yearly;result["promotion_screen"]=evaluate_backtest(result,yearly,ValidationGate())
    Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({"coverage":result["data_coverage"],"data_quality":quality,"metrics":{k:result[k] for k in ("trades","return_percent","profit_factor","expectancy_per_trade","max_drawdown_percent","win_rate_percent")},"yearly_pnl":yearly,"promotion_screen":result["promotion_screen"]},indent=2))
if __name__=="__main__":main()
