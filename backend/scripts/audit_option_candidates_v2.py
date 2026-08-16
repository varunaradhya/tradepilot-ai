from __future__ import annotations
import argparse,json,sqlite3,time,sys,statistics
from pathlib import Path
BACKEND=Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path: sys.path.insert(0,str(BACKEND))
from app.services.strategy_validation import _stats

def enrich(rows):
 rows=sorted(rows,key=lambda r:r['timestamp']); closes=[float(r['close']) for r in rows]; k20=2/21;k50=2/51; e20=[];e50=[]; a=b=closes[0] if closes else 0
 for c in closes:
  a=c*k20+a*(1-k20); b=c*k50+b*(1-k50); e20.append(a);e50.append(b)
 out=[]
 for i,r in enumerate(rows):
  start=max(0,i-20); avg=sum(float(x.get('volume') or 0) for x in rows[start:i])/max(i-start,1)
  out.append({**r,'ema20':e20[i],'ema50':e50[i],'rel_volume':float(r.get('volume') or 0)/avg if avg else 0})
 return out

def signal(r,conds):
 for c in conds:
  if c=='premium_trend' and not r['ema20']>r['ema50']: return False
  if c=='premium_weak' and not r['ema20']<r['ema50']: return False
  if c=='relvol_1_5' and not r['rel_volume']>=1.5: return False
  if c=='iv_high' and not float(r.get('iv') or 0)>20: return False
  if c=='iv_low' and not (0<float(r.get('iv') or 0)<15): return False
  if c=='oi_present' and not float(r.get('oi') or 0)>0: return False
 return True

def returns(rows,conds,horizon,cost,slip):
 friction=(cost+slip)/10000; out=[]
 for i in range(len(rows)-horizon):
  if signal(rows[i],conds): out.append(float(rows[i+horizon]['close'])/float(rows[i]['close'])-1-friction)
 return out

def main():
 p=argparse.ArgumentParser(description='Audit rolling-option candidates across neighboring strikes and calendar years; this is a research gate, not exact-contract validation.')
 p.add_argument('--db',default='data/research/market_data.sqlite'); p.add_argument('--input',default='data/research/option_validation_v1.json'); p.add_argument('--out',default='data/research/option_audit_v2.json'); p.add_argument('--horizon',type=int,default=6); p.add_argument('--cost-bps',type=float,default=5); p.add_argument('--slippage-bps',type=float,default=5)
 a=p.parse_args(); started=time.time(); src=json.loads(Path(a.input).read_text()); candidates=src.get('eligible',[]); db=sqlite3.connect(a.db); result={'input':a.input,'candidate_count':len(candidates),'eligible':[],'note':'Uses Dhan rolling expired-option data. Exact historical contract/expiry execution is not claimed by this audit.'}
 try:
  groups={}
  group_specs=list(db.execute('SELECT side,strike_key,COUNT(*) FROM option_bars GROUP BY side,strike_key HAVING COUNT(*)>=200 ORDER BY side,strike_key'))
  print(f'OPTION AUDIT V2: loading {len(group_specs)} option groups...',flush=True)
  for gi,(side,strike,n) in enumerate(group_specs,1):
   print(f'OPTION AUDIT V2: loading group {gi}/{len(group_specs)} {side}:{strike} rows={n}',flush=True)
   rows=[dict(zip(('timestamp','side','strike_key','strike','open','high','low','close','volume','oi','iv','spot'),r)) for r in db.execute('SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp',(side,strike))]
   groups[(side,strike)]=enrich(rows)
   if gi%5==0 or gi==len(group_specs): print(f'OPTION AUDIT V2: prepared {gi}/{len(group_specs)} groups elapsed={time.time()-started:.1f}s',flush=True)
  print(f'OPTION AUDIT V2: preparation complete; candidates={len(candidates)}',flush=True)
  for i,c in enumerate(candidates,1):
   print(f'OPTION AUDIT V2: candidate {i}/{len(candidates)} {c.get("name","?")} starting...',flush=True)
   parts=c['name'].split(':'); side,strike=parts[:2]; conds=parts[2:]; all_stats=[]; years={}
   same_side=[(k,rows) for (s,k),rows in groups.items() if s==side]
   for gi,(k,rows) in enumerate(same_side,1):
    vals=returns(rows,conds,a.horizon,a.cost_bps,a.slippage_bps)
    if len(vals)>=25:
     n,e,w,pf,total=_stats(vals); all_stats.append({'strike_key':k,'trades':n,'expectancy':e,'win_rate':w,'profit_factor':pf,'return':total})
     for y in range(2021,2027):
      yr=[r for r in rows if __import__('datetime').datetime.fromtimestamp(int(r['timestamp'])).year==y]; yv=returns(yr,conds,a.horizon,a.cost_bps,a.slippage_bps)
      if yv: years.setdefault(str(y),_stats(yv)[1])
   target_years={str(y):years.get(str(y),0) for y in range(2021,2027)}; positive_years=sum(v>0 for v in target_years.values()); positive_groups=sum(x['expectancy']>0 for x in all_stats); median_exp=statistics.median(x['expectancy'] for x in all_stats) if all_stats else 0; worst_exp=min((x['expectancy'] for x in all_stats),default=0); eligible=(len(all_stats)>=5 and positive_groups/len(all_stats)>=0.60 and median_exp>0 and positive_years>=4)
   item={**c,'cross_strike_groups':len(all_stats),'positive_strike_groups':positive_groups,'median_cross_strike_expectancy':median_exp,'worst_cross_strike_expectancy':worst_exp,'positive_years':positive_years,'yearly_expectancy':target_years,'rolling_generalization_eligible':eligible}; result['eligible'].append(item) if eligible else None
   print(f'OPTION AUDIT V2: candidate {i}/{len(candidates)} done eligible={eligible} rolling-generalized={len(result["eligible"])} elapsed={time.time()-started:.1f}s',flush=True)
 finally: db.close()
 result['elapsed_seconds']=round(time.time()-started,2); Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'candidates':len(candidates),'rolling_generalized':len(result['eligible']),'elapsed_seconds':result['elapsed_seconds'],'out':a.out},indent=2),flush=True)
if __name__=='__main__': main()
