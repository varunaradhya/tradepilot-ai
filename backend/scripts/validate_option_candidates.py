from __future__ import annotations
import argparse,json,sqlite3,sys,time
from pathlib import Path
BACKEND=Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path: sys.path.insert(0,str(BACKEND))
from app.services.option_pattern_discovery import discover_option_patterns
from app.services.strategy_validation import _stats,_drawdown

def option_returns(rows, condition_names, horizon, cost_bps, slippage_bps):
 rows=sorted(rows,key=lambda r:r['timestamp']); closes=[float(r['close']) for r in rows]; out=[]; friction=(cost_bps+slippage_bps)/10000
 for i in range(len(rows)-horizon):
  r=rows[i]; ok=True
  for name in condition_names:
   if name=='premium_trend': ok &= float(r.get('ema20',r['close']))>float(r.get('ema50',r['close']))
   elif name=='premium_weak': ok &= float(r.get('ema20',r['close']))<float(r.get('ema50',r['close']))
   elif name=='relvol_1_5': ok &= float(r.get('rel_volume',0))>=1.5
   elif name=='iv_high': ok &= float(r.get('iv',0))>20
   elif name=='iv_low': ok &= 0<float(r.get('iv',0))<15
   elif name=='oi_present': ok &= float(r.get('oi',0))>0
  if ok: out.append(closes[i+horizon]/closes[i]-1-friction)
 return out

def enrich(rows):
 rows=sorted(rows,key=lambda r:r['timestamp']); closes=[float(r['close']) for r in rows]; k20=2/21;k50=2/51; e20=[];e50=[]; a=b=closes[0]
 for c in closes:
  a=c*k20+a*(1-k20);b=c*k50+b*(1-k50);e20.append(a);e50.append(b)
 out=[]
 for i,r in enumerate(rows):
  start=max(0,i-20); avg=sum(float(x.get('volume') or 0) for x in rows[start:i])/max(i-start,1)
  out.append({**r,'ema20':e20[i],'ema50':e50[i],'rel_volume':float(r.get('volume') or 0)/avg if avg else 0})
 return out

def validate(rows, candidate, horizon, cost_bps, slippage_bps):
 name=candidate['name']; parts=name.split(':'); side=parts[0]; strike=parts[1]; conditions=parts[2:]; g=[r for r in rows if r.get('side')==side and r.get('strike_key')==strike]; g=enrich(g); n=len(g); a=int(n*.60);b=int(n*.80)
 sets=[g[:a],g[a:b],g[b:]]; stats=[]
 for s in sets:
  vals=option_returns(s,conditions,horizon,cost_bps,slippage_bps); stats.append(_stats(vals))
 tn,te,tw,tpf,tr=stats[0]; vn,ve,vw,vpf,vr=stats[1]; fn,fe,fw,fpf,fr=stats[2]; dd=_drawdown(option_returns(sets[2],conditions,horizon,cost_bps,slippage_bps)); reasons=[]
 if tn<50: reasons.append('insufficient_train_trades')
 if vn<25: reasons.append('insufficient_validation_trades')
 if fn<25: reasons.append('insufficient_final_trades')
 if te<=0: reasons.append('negative_train_expectancy')
 if ve<=0: reasons.append('negative_validation_expectancy')
 if fe<=0: reasons.append('negative_final_expectancy')
 if fpf is not None and fpf<1.10: reasons.append('weak_final_profit_factor')
 return {'name':name,'side':side,'strike_key':strike,'train_trades':tn,'validation_trades':vn,'final_trades':fn,'train_expectancy':te,'validation_expectancy':ve,'final_expectancy':fe,'final_win_rate':fw,'final_profit_factor':fpf,'final_drawdown':dd,'eligible':not reasons,'rejection_reasons':reasons}

def main():
 p=argparse.ArgumentParser();p.add_argument('--db',default='data/research/market_data.sqlite');p.add_argument('--input',default='data/research/option_pattern_lab_v1.json');p.add_argument('--out',default='data/research/option_validation_v1.json');p.add_argument('--horizon',type=int,default=6);p.add_argument('--cost-bps',type=float,default=5);p.add_argument('--slippage-bps',type=float,default=5);a=p.parse_args(); started=time.time();db=sqlite3.connect(a.db);src=json.loads(Path(a.input).read_text());candidates=src.get('top_candidates',[]);report={'candidates':len(candidates),'eligible':[],'results':[]}
 try:
  for i,c in enumerate(candidates,1):
   side=c['name'].split(':')[0]; strike=c['name'].split(':')[1]; rows=[dict(zip(('timestamp','side','strike_key','strike','open','high','low','close','volume','oi','iv','spot'),r)) for r in db.execute('SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp',(side,strike))]; v=validate(rows,c,a.horizon,a.cost_bps,a.slippage_bps);report['results'].append(v)
   
   if v['eligible']: report['eligible'].append(v)
   if i%5==0 or i==len(candidates): print(f'OPTION VALIDATION: {i}/{len(candidates)} eligible={len(report["eligible"])}',flush=True)
 finally: db.close()
 report['elapsed_seconds']=round(time.time()-started,2);Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(report,indent=2));print(json.dumps({'candidates':len(candidates),'eligible':len(report['eligible']),'elapsed_seconds':report['elapsed_seconds'],'out':a.out},indent=2),flush=True)
if __name__=='__main__':main()
