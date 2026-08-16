from __future__ import annotations
import argparse,json,os,sys
from datetime import date
from pathlib import Path
BACKEND_DIR=Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path: sys.path.insert(0,str(BACKEND_DIR))
from app.brokers.dhan import DhanClient
from app.services.fno_research_pipeline import chunk_date_range,validate_bars
from app.services.option_research_pipeline import OptionResearchConfig,normalize_rolling,normalize_spot,simulate_option_days,summarize
from app.services.fno_strategy_v1 import FNOORBConfig

def dedupe(rows):
    seen={};
    for r in rows: seen[(r.get('side'),r.get('timestamp'),r.get('strike'))]=r
    return sorted(seen.values(),key=lambda x:(x.get('timestamp'),x.get('side','')))

def main():
    p=argparse.ArgumentParser(description='Five-year option-first V1 research using Dhan rolling expired-options data.')
    p.add_argument('--security-id',default='13'); p.add_argument('--from-date',required=True); p.add_argument('--to-date',required=True); p.add_argument('--out',default='data/research/options_v1.json'); p.add_argument('--expiry-flag',default='WEEK'); p.add_argument('--expiry-code',type=int,default=0); p.add_argument('--strike',default='ATM'); p.add_argument('--capital',type=float,default=100000); p.add_argument('--lot-size',type=int,default=65)
    a=p.parse_args(); cid=os.environ.get('DHAN_CLIENT_ID'); token=os.environ.get('DHAN_ACCESS_TOKEN')
    if not cid or not token: raise SystemExit('Set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN before running research.')
    start=date.fromisoformat(a.from_date); end=date.fromisoformat(a.to_date)
    if start>=end: raise SystemExit('from-date must be earlier than to-date')
    client=DhanClient(cid,token); spot=[]; options=[]; windows=chunk_date_range(start,end,30)
    print(f'Downloading option research: {len(windows)} x 30-day windows ({a.from_date} -> {a.to_date})')
    for n,w in enumerate(windows,1):
        print(f'[{n}/{len(windows)}] {w.start} -> {w.end}')
        s=client.historical_intraday(a.security_id,'IDX_I','INDEX','5',w.start.isoformat(),w.end.isoformat(),oi=False,expiry_code=0)
        spot.extend(normalize_spot(s))
        for typ in ('CALL','PUT'):
            r=client.rolling_option(a.security_id,a.expiry_flag,a.expiry_code,a.strike,typ,w.start.isoformat(),w.end.isoformat(),'5')
            got=normalize_rolling(r); options.extend(got); print(f'  {typ}: {len(got)} rows')
    spot=dedupe(spot); options=dedupe(options); quality=validate_bars(spot)
    if not quality['quality_ok']: raise SystemExit(f'Underlying data quality gate failed: {quality}')
    cfg=OptionResearchConfig(capital=a.capital,lot_size=a.lot_size,expiry_flag=a.expiry_flag,expiry_code=a.expiry_code,strike=a.strike)
    trades=simulate_option_days(spot,options,cfg,FNOORBConfig()); metrics=summarize(trades)
    yearly={}
    for t in trades: yearly[t['date'][:4]]=yearly.get(t['date'][:4],0.0)+float(t['pnl'])
    result={'strategy':'NIFTY ATM weekly option V1','status':'RESEARCH_ONLY','data_source':'Dhan rolling expired options + NIFTY index','coverage':{'from':a.from_date,'to':a.to_date,'spot_bars':len(spot),'option_rows':len(options),'windows':len(windows)},'data_quality':quality,'metrics':metrics,'yearly_pnl':yearly,'trades':trades,'contract_lock_note':'Dhan rolling-options endpoint returns strike-wise rolling data; this run locks the returned strike after entry but is not yet eligible for production promotion until exact-expiry contract validation is added.','promotion_eligible':False}
    Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'coverage':result['coverage'],'data_quality':quality,'metrics':metrics,'yearly_pnl':yearly,'promotion_eligible':False},indent=2))
if __name__=='__main__': main()
