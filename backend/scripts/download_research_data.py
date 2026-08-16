from __future__ import annotations
import argparse, os, sys
from datetime import date
from pathlib import Path
BACKEND=Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path: sys.path.insert(0,str(BACKEND))
from app.brokers.dhan import DhanClient
from app.services.fno_research_pipeline import chunk_date_range
from app.services.option_research_pipeline import normalize_rolling, normalize_spot
from app.services.research_data_cache import ResearchDataCache

def main():
    p=argparse.ArgumentParser(description='Download and persist Dhan research data once for repeated strategy tests.')
    p.add_argument('--security-id',default='13'); p.add_argument('--from-date',required=True); p.add_argument('--to-date',required=True)
    p.add_argument('--interval',default='5',choices=['1','5','15','25','60'])
    p.add_argument('--expiry-flag',default='WEEK',choices=['WEEK','MONTH'])
    p.add_argument('--expiry-code',type=int,default=0)
    p.add_argument('--strikes',default='ATM,ATM-1,ATM+1,ATM-2,ATM+2,ATM-3,ATM+3,ATM-4,ATM+4,ATM-5,ATM+5,ATM-6,ATM+6,ATM-7,ATM+7,ATM-8,ATM+8,ATM-9,ATM+9,ATM-10,ATM+10')
    p.add_argument('--db',default='data/research/market_data.sqlite')
    a=p.parse_args(); cid=os.environ.get('DHAN_CLIENT_ID'); token=os.environ.get('DHAN_ACCESS_TOKEN')
    if not cid or not token: raise SystemExit('Set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN before downloading research data.')
    start=date.fromisoformat(a.from_date); end=date.fromisoformat(a.to_date)
    if start>=end: raise SystemExit('from-date must be earlier than to-date')
    strikes=[x.strip().upper() for x in a.strikes.split(',') if x.strip()]
    dataset_id=f'nifty_options_{a.expiry_flag.lower()}_{a.interval}m_atm10'
    metadata={'security_id':a.security_id,'expiry_flag':a.expiry_flag,'expiry_code':a.expiry_code,'strikes':strikes,'interval':a.interval,'fields':['OHLC','IV','VOLUME','OI','SPOT'],'source':'Dhan rolling expired options + Dhan historical intraday'}
    client=DhanClient(cid,token); windows=chunk_date_range(start,end,30)
    with ResearchDataCache(a.db) as cache:
        cache.dataset(dataset_id,'Dhan',a.interval,a.from_date,a.to_date,metadata)
        total=len(windows); print(f'Dataset: {dataset_id} | {total} windows | {len(strikes)} strikes x 2 sides')
        for n,w in enumerate(windows,1):
            key=f'{w.start}:{w.end}'
            if cache.done(dataset_id,key): print(f'[{n}/{total}] cached {w.start} -> {w.end}'); continue
            print(f'[{n}/{total}] {w.start} -> {w.end}')
            spot=client.historical_intraday(a.security_id,'IDX_I','INDEX',a.interval,w.start.isoformat(),w.end.isoformat(),oi=False,expiry_code=0)
            spot_rows=normalize_spot(spot); cache.put_spot(spot_rows)
            rows=[]
            for strike in strikes:
                for typ in ('CALL','PUT'):
                    raw=client.rolling_option(a.security_id,a.expiry_flag,a.expiry_code,strike,typ,w.start.isoformat(),w.end.isoformat(),a.interval)
                    got=normalize_rolling(raw)
                    for r in got: r['strike_key']=strike
                    rows.extend(got)
            cache.put_options(rows); cache.mark_done(dataset_id,key)
            print(f'  spot={len(spot_rows)} option_rows={len(rows)} cache={cache.counts()}')
        print('DOWNLOAD COMPLETE')
        print(cache.counts())

if __name__=='__main__': main()
