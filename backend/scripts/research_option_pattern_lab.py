from __future__ import annotations
import argparse,json,sqlite3,sys,time
from pathlib import Path
BACKEND=Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path: sys.path.insert(0,str(BACKEND))
from app.services.option_pattern_discovery import discover_option_patterns

def main():
    p=argparse.ArgumentParser(description='Memory-safe exploratory pattern scan across cached NIFTY option contracts.')
    p.add_argument('--db',default='data/research/market_data.sqlite'); p.add_argument('--horizon',type=int,default=6); p.add_argument('--min-occurrences',type=int,default=100); p.add_argument('--out',default='data/research/option_pattern_lab_v1.json'); a=p.parse_args()
    started=time.time(); db=sqlite3.connect(a.db); report={'horizon_bars':a.horizon,'min_occurrences':a.min_occurrences,'groups':{}}
    try:
        groups=list(db.execute('SELECT side,strike_key,COUNT(*) FROM option_bars GROUP BY side,strike_key HAVING COUNT(*)>=? ORDER BY side,strike_key',(max(2*a.min_occurrences,200),))); print(f'OPTION PATTERN LAB: groups={len(groups)} | min_rows_per_group={max(2*a.min_occurrences,200)}',flush=True)
        all_results=[]
        for i,(side,strike_key,count) in enumerate(groups,1):
            rows=[dict(zip(('timestamp','side','strike_key','strike','open','high','low','close','volume','oi','iv','spot'),r)) for r in db.execute('SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp',(side,strike_key))]
            results=discover_option_patterns(rows,a.horizon,a.min_occurrences); robust=sum(r.robust for r in results); report['groups'][f'{side}:{strike_key}']={'rows':len(rows),'candidate_count':len(results),'robust_count':robust,'top':[r.to_dict() for r in results[:5]]}; all_results.extend(results); print(f'OPTION PATTERN LAB: {i}/{len(groups)} {side}:{strike_key} rows={len(rows):,} candidates={len(results)} robust={robust}',flush=True)
        all_results.sort(key=lambda x:(x.robust,x.test_score),reverse=True); report['top_candidates']=[r.to_dict() for r in all_results[:50]]
    finally: db.close()
    report['elapsed_seconds']=round(time.time()-started,2); Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps({'groups':len(report['groups']),'candidate_count':sum(x['candidate_count'] for x in report['groups'].values()),'robust_count':sum(x['robust_count'] for x in report['groups'].values()),'elapsed_seconds':report['elapsed_seconds'],'out':a.out},indent=2),flush=True)
if __name__=='__main__': main()
