from __future__ import annotations
import argparse, json, sqlite3, statistics, time
from collections import defaultdict
from pathlib import Path


def parse_name(n):
    p=n.split(':'); return p[0], p[1] if len(p)>1 else '', tuple(sorted(x for x in (p[2].split('+') if len(p)>2 else []) if x and x!='base'))
def family_sig(n):
    p=n.split(':'); return p[0], tuple(sorted(x for x in ((p[2].split('+') if len(p)>2 else p[1].split('+') if len(p)==2 else [])) if x and x!='base'))

def enrich(rows):
    rows=sorted(rows,key=lambda r:r['timestamp']); c=[float(r['close']) for r in rows]
    if not c:return []
    a=b=c[0]; k20,k50=2/21,2/51; e20=[]; e50=[]
    for x in c:a=x*k20+a*(1-k20); b=x*k50+b*(1-k50); e20.append(a); e50.append(b)
    out=[]
    for i,r in enumerate(rows):
        prior=rows[max(0,i-20):i]; avg=sum(float(x.get('volume') or 0) for x in prior)/max(1,len(prior))
        out.append({**r,'ema20':e20[i],'ema50':e50[i],'rel_volume':float(r.get('volume') or 0)/avg if avg else 0})
    return out

def signal(r,cond):
    return all((c!='premium_trend' or r['ema20']>r['ema50']) and (c!='premium_weak' or r['ema20']<r['ema50']) and (c!='relvol_1_5' or r['rel_volume']>=1.5) and (c!='iv_high' or float(r.get('iv') or 0)>20) and (c!='iv_low' or 0<float(r.get('iv') or 0)<15) and (c!='oi_present' or float(r.get('oi') or 0)>0) for c in cond)

def build(rows,family,cond,horizon,friction,rank):
    e=enrich(rows); out=[]
    for i in range(len(e)-horizon):
        r=e[i]
        if not signal(r,cond):continue
        entry=float(r['close']); exit_=float(e[i+horizon]['close'])
        if entry<=0 or exit_<0:continue
        out.append({'timestamp':r['timestamp'],'exit_timestamp':e[i+horizon]['timestamp'],'return':max(exit_/entry-1-friction,-1),'family':family,'family_rank':rank,'strike_key':r['strike_key']})
    return out

def folds(ts,n):
    u=sorted(set(ts)); n=max(1,min(n,len(u))); return [(u[(i*len(u))//n],u[((i+1)*len(u))//n] if i<n-1 else u[-1],i==n-1) for i in range(n)] if u else []

def simulate(events,initial,alloc,maxpos):
    by=defaultdict(list)
    for e in events:by[e['timestamp']].append(e)
    fixed=initial*alloc; cash=initial; active=[]; done=[]; skipped=0; maxexp=0; peak=initial; dd=0
    for ts in sorted(by):
        keep=[]
        for p in active:
            if p['exit_timestamp']<=ts:cash+=p['position_value']+p['pnl']; done.append(p)
            else:keep.append(p)
        active=keep; used=sum(p['position_value'] for p in active)
        for c in sorted(by[ts],key=lambda x:(x['family_rank'],x['family'],x['strike_key']))[:1]:
            if len(active)>=maxpos or used+fixed>initial or cash<fixed:skipped+=1; continue
            cash-=fixed; p={**c,'position_value':fixed,'pnl':fixed*c['return']}; active.append(p); used+=fixed; maxexp=max(maxexp,used/initial)
        equity=cash+sum(p['position_value']+p['pnl'] for p in active); peak=max(peak,equity); dd=min(dd,equity/peak-1 if peak else 0)
    for p in sorted(active,key=lambda x:x['exit_timestamp']):cash+=p['position_value']+p['pnl']; done.append(p)
    pnls=[p['pnl'] for p in done]; wins=[x for x in pnls if x>0]; losses=[-x for x in pnls if x<0]
    return {'trades':len(done),'win_rate':len(wins)/len(done) if done else 0,'expectancy':statistics.mean([p['return'] for p in done]) if done else 0,'profit_factor':sum(wins)/sum(losses) if losses else (float('inf') if wins else None),'return_pct':sum(pnls)/initial if initial else 0,'max_drawdown_pct':dd,'max_exposure_pct':maxexp,'skipped':skipped,'trades_data':done}

def main():
    p=argparse.ArgumentParser(description='V11 chronological robustness audit; not independent OOS discovery.'); p.add_argument('--db',default='data/research/market_data.sqlite'); p.add_argument('--input',default='data/research/option_family_v6.json'); p.add_argument('--out',default='data/research/option_family_v11.json'); p.add_argument('--horizon',type=int,default=6); p.add_argument('--cost-bps',type=float,default=5); p.add_argument('--slippage-bps',type=float,default=5); p.add_argument('--initial-capital',type=float,default=100000); p.add_argument('--allocation-pct',type=float,default=.02); p.add_argument('--max-positions',type=int,default=5); p.add_argument('--folds',type=int,default=4); p.add_argument('--min-trades-per-fold',type=int,default=500); p.add_argument('--min-positive-fold-rate',type=float,default=.75); p.add_argument('--max-top-family-pnl-share',type=float,default=.70); a=p.parse_args(); start=time.time()
    src=json.loads(Path(a.input).read_text()); fam=[r for r in src.get('results',[]) if r.get('eligible_for_next_research_gate')]
    if not fam:raise SystemExit('V11 requires V6 eligible families.')
    names=[r['family'] for r in fam]; rank={n:i for i,n in enumerate(names)}
    db=sqlite3.connect(a.db); db.row_factory=sqlite3.Row; cols=[r['name'] for r in db.execute('PRAGMA table_info(option_bars)')]
    identity_coverage=0
    if 'contract_identity' in cols:
        total,nonnull=db.execute('SELECT COUNT(*),COUNT(contract_identity) FROM option_bars').fetchone(); identity_coverage=nonnull/total if total else 0
    specs=sorted({(parse_name(n)[0],parse_name(n)[1]) for f in fam for n in f.get('matched_candidate_names',[])}); groups={}; all_ts=[]
    for side,strike in specs:
        rows=[dict(r) for r in db.execute('SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp',(side,strike))]; groups[(side,strike)]=rows; all_ts.extend(r['timestamp'] for r in rows)
    db.close()
    friction=(a.cost_bps+a.slippage_bps)/10000; events=[]
    for f in fam:
        name=f['family']; side,cond=family_sig(name)
        for n in f.get('matched_candidate_names',[]):
            cs,strike,cc=parse_name(n)
            if cs==side and cc==cond:events.extend(build(groups.get((cs,strike),[]),name,cond,a.horizon,friction,rank[name]))
    events.sort(key=lambda x:(x['timestamp'],x['family_rank'],x['strike_key'])); fs=folds(all_ts,a.folds); reports=[]
    for i,(lo,hi,last) in enumerate(fs,1):
        ev=[e for e in events if lo<=e['timestamp']<hi or (last and e['timestamp']==hi)]; r=simulate(ev,a.initial_capital,a.allocation_pct,a.max_positions); fam_pnl=defaultdict(float)
        for t in r['trades_data']:fam_pnl[t['family']]+=t['pnl']
        pos=sum(v for v in fam_pnl.values() if v>0); top=max(fam_pnl.values(),default=0)/pos if pos>0 else 0
        reports.append({k:v for k,v in r.items() if k!='trades_data'}|{'fold':i,'start_timestamp':lo,'end_timestamp':hi,'top_family_positive_pnl_share':top,'family_pnl':dict(sorted(fam_pnl.items(),key=lambda x:x[1],reverse=True))})
        print(f"OPTION FAMILY V11: fold={i} trades={r['trades']} return={r['return_pct']:.2%} PF={r['profit_factor']} DD={r['max_drawdown_pct']:.2%} top_family_share={top:.2%}",flush=True)
    populated=[r for r in reports if r['trades']]; positive=[r for r in populated if r['return_pct']>0]; worst_pf=min((r['profit_factor'] for r in populated if r['profit_factor'] is not None),default=None); top_share=max((r['top_family_positive_pnl_share'] for r in populated),default=0); total=simulate(events,a.initial_capital,a.allocation_pct,a.max_positions); reasons=[]
    if len(populated)<a.folds:reasons.append('missing_populated_folds')
    if any(r['trades']<a.min_trades_per_fold for r in populated):reasons.append('insufficient_trades_in_fold')
    if (len(positive)/len(populated) if populated else 0)<a.min_positive_fold_rate:reasons.append('weak_positive_fold_rate')
    if worst_pf is None or worst_pf<1.05:reasons.append('weak_worst_fold_profit_factor')
    if top_share>a.max_top_family_pnl_share:reasons.append('excessive_family_concentration')
    result={'version':'v11','methodology':{'purpose':'chronological stability and concentration audit after V10','folds':len(fs),'horizon_bars':a.horizon,'friction_bps':a.cost_bps+a.slippage_bps,'initial_capital':a.initial_capital,'allocation_pct':a.allocation_pct,'max_positions':a.max_positions,'selection_rule':'fixed V7 family rank; top family per timestamp','important_limitation':'V5/V6 family selection used the full historical dataset; therefore V11 is temporal robustness, not independent OOS discovery.'},'data_quality':{'contract_identity_coverage':identity_coverage,'identity_note':'Current Dhan rolling-series identity is synthetic and is not exact exchange expiry/contract identity.'},'families':names,'folds':reports,'aggregate':{k:v for k,v in total.items() if k!='trades_data'},'gate_metrics':{'populated_folds':len(populated),'positive_fold_rate':len(positive)/len(populated) if populated else 0,'worst_fold_profit_factor':worst_pf,'max_top_family_positive_pnl_share':top_share},'gate_reasons':reasons,'next_gate':not reasons,'promotion_status':'RESEARCH_ONLY_NO_PAPER_TRADING','elapsed_seconds':round(time.time()-start,2)}
    Path(a.out).write_text(json.dumps(result,indent=2)); print(json.dumps({'families':len(names),'folds':len(fs),'populated_folds':len(populated),'positive_fold_rate':result['gate_metrics']['positive_fold_rate'],'worst_fold_pf':worst_pf,'next_gate':result['next_gate'],'out':a.out,'elapsed_seconds':result['elapsed_seconds']},indent=2),flush=True)

if __name__=='__main__':main()
