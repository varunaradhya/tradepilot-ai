from __future__ import annotations
import argparse,json,sqlite3,sys,time
from pathlib import Path
BACKEND=Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path: sys.path.insert(0,str(BACKEND))
from app.services.pattern_discovery import discover_patterns, discover_equity_patterns


def fetch_equity(db,symbol,dataset):
    rows=db.execute('SELECT timestamp,open,high,low,close,volume FROM equity_bars WHERE dataset_id=? AND symbol=? ORDER BY timestamp',(dataset,symbol))
    return [dict(zip(('timestamp','open','high','low','close','volume'),r)) for r in rows]

def main():
    p=argparse.ArgumentParser(description='Automated exploratory pattern scan across the validated research cache.')
    p.add_argument('--db',default='data/research/market_data.sqlite'); p.add_argument('--equity-dataset',default='equity_nse_discovery_5m'); p.add_argument('--horizon',type=int,default=6); p.add_argument('--min-occurrences',type=int,default=100); p.add_argument('--out',default='data/research/pattern_lab_v1.json'); p.add_argument('--include-nifty',action='store_true'); a=p.parse_args()
    started=time.time(); db=sqlite3.connect(a.db); report={'dataset':a.equity_dataset,'horizon_bars':a.horizon,'min_occurrences':a.min_occurrences,'equity':{},'nifty':None}
    try:
        symbols=[r[0] for r in db.execute('SELECT DISTINCT symbol FROM equity_bars WHERE dataset_id=? ORDER BY symbol',(a.equity_dataset,))]; total=len(symbols)+(1 if a.include_nifty else 0); done=0
        print(f'PATTERN LAB: starting | equity_symbols={len(symbols)} | total_series={total}',flush=True)
        for symbol in symbols:
            done+=1; rows=fetch_equity(db,symbol,a.equity_dataset); print(f'PATTERN LAB: equity {done}/{total} {symbol} rows={len(rows):,} discovering...',flush=True)
            results=discover_equity_patterns(rows,a.horizon,a.min_occurrences); robust=sum(r.robust for r in results); report['equity'][symbol]={'rows':len(rows),'candidate_count':len(results),'robust_count':robust,'top':[r.to_dict() for r in results[:10]]}; print(f'PATTERN LAB: {symbol} candidates={len(results)} robust={robust}',flush=True)
        if a.include_nifty:
            done+=1; rows=[dict(zip(('timestamp','open','high','low','close','volume'),r)) for r in db.execute('SELECT timestamp,open,high,low,close,volume FROM spot_bars ORDER BY timestamp')]; print(f'PATTERN LAB: NIFTY {done}/{total} rows={len(rows):,} discovering...',flush=True); results=discover_patterns(rows,a.horizon,a.min_occurrences); robust=sum(r.robust for r in results); report['nifty']={'rows':len(rows),'candidate_count':len(results),'robust_count':robust,'top':[r.to_dict() for r in results[:20]]}; print(f'PATTERN LAB: NIFTY candidates={len(results)} robust={robust}',flush=True)
    finally: db.close()
    report['elapsed_seconds']=round(time.time()-started,2); Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(report,indent=2),encoding='utf-8'); total_candidates=sum(x['candidate_count'] for x in report['equity'].values())+(report['nifty']['candidate_count'] if report['nifty'] else 0); total_robust=sum(x['robust_count'] for x in report['equity'].values())+(report['nifty']['robust_count'] if report['nifty'] else 0); print(json.dumps({'series':total,'candidate_count':total_candidates,'robust_count':total_robust,'elapsed_seconds':report['elapsed_seconds'],'out':a.out},indent=2),flush=True)

if __name__=='__main__': main()
