from __future__ import annotations
import argparse,json,sqlite3,sys,time
from pathlib import Path
BACKEND=Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path: sys.path.insert(0,str(BACKEND))
from app.services.pattern_discovery import enrich_bars
from app.services.strategy_validation import validate_rule

def main():
 p=argparse.ArgumentParser(description='Validate discovered equity candidates on untouched final data with costs and slippage.')
 p.add_argument('--db',default='data/research/market_data.sqlite'); p.add_argument('--dataset',default='equity_nse_discovery_5m'); p.add_argument('--input',default='data/research/pattern_lab_v1.json'); p.add_argument('--out',default='data/research/equity_validation_v1.json'); p.add_argument('--horizon',type=int,default=6); p.add_argument('--cost-bps',type=float,default=3); p.add_argument('--slippage-bps',type=float,default=2); a=p.parse_args()
 started=time.time(); db=sqlite3.connect(a.db); source=json.loads(Path(a.input).read_text(encoding='utf-8')); report={'dataset':a.dataset,'cost_bps':a.cost_bps,'slippage_bps':a.slippage_bps,'symbols':{},'eligible':[]}
 try:
  for i,(symbol,info) in enumerate(source.get('equity',{}).items(),1):
   rows=[dict(zip(('timestamp','open','high','low','close','volume'),r)) for r in db.execute('SELECT timestamp,open,high,low,close,volume FROM equity_bars WHERE dataset_id=? AND symbol=? ORDER BY timestamp',(a.dataset,symbol))]
   rows=enrich_bars(rows); candidates=info.get('top',[]); results=[]
   print(f'VALIDATION: {i}/{len(source.get("equity",{}))} {symbol} candidates={len(candidates)}',flush=True)
   for c in candidates:
    v=validate_rule(rows,c['name'],a.horizon,cost_bps=a.cost_bps,slippage_bps=a.slippage_bps); results.append(v.to_dict())
   eligible=[r for r in results if r['eligible']]; report['symbols'][symbol]={'candidates':len(results),'eligible':len(eligible),'results':results}; report['eligible'] += [{'symbol':symbol,**r} for r in eligible]
 finally: db.close()
 report['elapsed_seconds']=round(time.time()-started,2); Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps({'symbols':len(report['symbols']),'eligible':len(report['eligible']),'elapsed_seconds':report['elapsed_seconds'],'out':a.out},indent=2),flush=True)
if __name__=='__main__': main()
