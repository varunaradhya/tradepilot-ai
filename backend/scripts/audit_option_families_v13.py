from __future__ import annotations
import argparse, json, sqlite3, statistics, time
from collections import defaultdict
from pathlib import Path


def parse_name(n):
    p=n.split(':')
    return p[0], p[1] if len(p)>1 else '', tuple(sorted(x for x in (p[2].split('+') if len(p)>2 else []) if x and x!='base'))


def family_sig(n):
    p=n.split(':')
    return p[0], tuple(sorted(x for x in ((p[2].split('+') if len(p)>2 else p[1].split('+') if len(p)==2 else [])) if x and x!='base'))


def enrich(rows):
    rows=sorted(rows,key=lambda r:r['timestamp'])
    c=[float(r['close']) for r in rows]
    if not c:return []
    a=b=c[0]; k20,k50=2/21,2/51; e20=[]; e50=[]
    for x in c:
        a=x*k20+a*(1-k20); b=x*k50+b*(1-k50); e20.append(a); e50.append(b)
    out=[]
    for i,r in enumerate(rows):
        prior=rows[max(0,i-20):i]
        avg=sum(float(x.get('volume') or 0) for x in prior)/max(1,len(prior))
        out.append({**r,'ema20':e20[i],'ema50':e50[i],'rel_volume':float(r.get('volume') or 0)/avg if avg else 0})
    return out


def signal(r,cond):
    for c in cond:
        if c=='premium_trend' and not r['ema20']>r['ema50']: return False
        if c=='premium_weak' and not r['ema20']<r['ema50']: return False
        if c=='relvol_1_5' and not r['rel_volume']>=1.5: return False
        if c=='iv_high' and not float(r.get('iv') or 0)>20: return False
        if c=='iv_low' and not 0<float(r.get('iv') or 0)<15: return False
        if c=='oi_present' and not float(r.get('oi') or 0)>0: return False
    return True


def build(rows,family,cond,horizon,friction,rank):
    e=enrich(rows); out=[]
    for i in range(len(e)-horizon):
        r=e[i]
        if not signal(r,cond):continue
        entry=float(r['close']); exit_=float(e[i+horizon]['close'])
        if entry<=0 or exit_<0:continue
        out.append({'timestamp':r['timestamp'],'exit_timestamp':e[i+horizon]['timestamp'],'return':max(exit_/entry-1-friction,-1),'family':family,'family_rank':rank,'strike_key':r['strike_key']})
    return out


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
        if by[ts]:
            c=sorted(by[ts],key=lambda x:(x['family_rank'],x['family'],x['strike_key']))[0]
            if len(active)>=maxpos or used+fixed>initial or cash<fixed:skipped+=1
            else:
                cash-=fixed; p={**c,'position_value':fixed,'pnl':fixed*c['return']}; active.append(p); used+=fixed; maxexp=max(maxexp,used/initial)
        equity=cash+sum(p['position_value']+p['pnl'] for p in active); peak=max(peak,equity); dd=min(dd,equity/peak-1 if peak else 0)
    for p in sorted(active,key=lambda x:x['exit_timestamp']):cash+=p['position_value']+p['pnl']; done.append(p)
    pnls=[p['pnl'] for p in done]; vals=[p['return'] for p in done]; wins=[x for x in pnls if x>0]; losses=[-x for x in pnls if x<0]
    pf=sum(wins)/sum(losses) if losses else (float('inf') if wins else None)
    return {'trades':len(done),'win_rate':len(wins)/len(done) if done else 0,'expectancy':statistics.mean(vals) if vals else 0,'profit_factor':pf,'return_pct':sum(pnls)/initial if initial else 0,'max_drawdown_pct':dd,'max_exposure_pct':maxexp,'skipped':skipped}


def percentile_split(ts,p):
    u=sorted(set(ts));
    if not u:return None
    idx=min(len(u)-1,max(0,int(len(u)*p)))
    return u[idx]


def main():
    p=argparse.ArgumentParser(description='V13 strict chronological OOS audit with frozen V6 family selection.')
    p.add_argument('--db',default='data/research/market_data.sqlite'); p.add_argument('--input',default='data/research/option_family_v6.json'); p.add_argument('--out',default='data/research/option_family_v13.json')
    p.add_argument('--horizon',type=int,default=6); p.add_argument('--cost-bps',type=float,default=5); p.add_argument('--slippage-bps',type=float,default=5); p.add_argument('--initial-capital',type=float,default=100000); p.add_argument('--allocation-pct',type=float,default=.02); p.add_argument('--max-positions',type=int,default=5); p.add_argument('--folds',type=int,default=5); p.add_argument('--min-trades-per-fold',type=int,default=200); p.add_argument('--holdout-pct',type=float,default=.20); a=p.parse_args(); start=time.time()
    src=json.loads(Path(a.input).read_text()); fam=[r for r in src.get('results',[]) if r.get('eligible_for_next_research_gate')]
    if not fam:raise SystemExit('V13 requires V6 eligible families.')
    names=[r['family'] for r in fam]; rank={n:i for i,n in enumerate(names)}
    db=sqlite3.connect(a.db); db.row_factory=sqlite3.Row
    cols=[r['name'] for r in db.execute('PRAGMA table_info(option_bars)')]
    if 'contract_identity' not in cols:raise SystemExit('V13 requires contract_identity column.')
    total,nonnull=db.execute('SELECT COUNT(*),COUNT(contract_identity) FROM option_bars').fetchone()
    if total==0 or nonnull!=total:raise SystemExit(f'V13 requires complete contract_identity coverage: {nonnull}/{total}')
    specs=sorted({(parse_name(n)[0],parse_name(n)[1]) for f in fam for n in f.get('matched_candidate_names',[])})
    groups={}; all_ts=[]
    for side,strike in specs:
        rows=[dict(r) for r in db.execute('SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp',(side,strike))]
        groups[(side,strike)]=rows; all_ts.extend(r['timestamp'] for r in rows)
    db.close()
    friction=(a.cost_bps+a.slippage_bps)/10000
    events=[]
    for f in fam:
        name=f['family']; side,cond=family_sig(name)
        for n in f.get('matched_candidate_names',[]):
            cs,strike,cc=parse_name(n)
            if cs==side and cc==cond:events.extend(build(groups.get((cs,strike),[]),name,cond,a.horizon,friction,rank[name]))
    events.sort(key=lambda x:(x['timestamp'],x['family_rank'],x['strike_key']))
    event_ts=sorted(set(e['timestamp'] for e in events))
    if len(event_ts)<a.folds*2:raise SystemExit('V13 requires enough chronological event timestamps for folds.')

    # Strict final holdout: the last holdout_pct of event timestamps is never used for any scoring/tuning.
    cut=percentile_split(event_ts,1-a.holdout_pct)
    holdout=[e for e in events if e['timestamp']>=cut]
    pre=[e for e in events if e['timestamp']<cut]
    h=simulate(holdout,a.initial_capital,a.allocation_pct,a.max_positions)
    print(f"OPTION FAMILY V13: strict_holdout start={cut} trades={h['trades']} return={h['return_pct']:.2%} PF={h['profit_factor']} DD={h['max_drawdown_pct']:.2%}",flush=True)

    # Chronological test folds over the pre-holdout history. Rules/family ranks remain frozen.
    u=sorted(set(e['timestamp'] for e in pre)); reports=[]
    for i in range(a.folds):
        lo=u[(i*len(u))//a.folds]; hi=u[((i+1)*len(u))//a.folds] if i<a.folds-1 else u[-1]
        ev=[e for e in pre if lo<=e['timestamp']<hi or (i==a.folds-1 and e['timestamp']==hi)]
        r=simulate(ev,a.initial_capital,a.allocation_pct,a.max_positions)
        reports.append({'fold':i+1,'start_timestamp':lo,'end_timestamp':hi,**r})
        print(f"OPTION FAMILY V13: pre_holdout_fold={i+1} trades={r['trades']} return={r['return_pct']:.2%} PF={r['profit_factor']} DD={r['max_drawdown_pct']:.2%}",flush=True)

    positive=[r for r in reports if r['trades']>=a.min_trades_per_fold and r['return_pct']>0]
    populated=[r for r in reports if r['trades']>=a.min_trades_per_fold]
    worst_pf=min((r['profit_factor'] for r in reports if r['profit_factor'] is not None),default=None)
    holdout_pf=h['profit_factor']
    holdout_pass=(h['trades']>=a.min_trades_per_fold and h['return_pct']>0 and holdout_pf is not None and holdout_pf>=1.10)
    reasons=[]
    if len(populated)<a.folds:reasons.append('insufficient_pre_holdout_fold_trades')
    if (len(positive)/len(populated) if populated else 0)<.75:reasons.append('weak_pre_holdout_positive_fold_rate')
    if worst_pf is None or worst_pf<1.10:reasons.append('weak_pre_holdout_worst_pf')
    if not holdout_pass:reasons.append('strict_holdout_failure')
    # Additional concentration check on the untouched holdout.
    fam_pnl=defaultdict(float)
    for e in holdout:
        pass
    # Reconstruct holdout trades to measure family concentration without changing the simulation result.
    # This intentionally uses the same frozen execution policy.
    # A compact per-family event approximation is sufficient for the gate.
    byfam=defaultdict(float)
    by=defaultdict(list)
    for e in holdout:by[e['timestamp']].append(e)
    fixed=a.initial_capital*a.allocation_pct; active=[]
    for ts in sorted(by):
        active=[p for p in active if p['exit_timestamp']>ts]
        used=sum(p['position_value'] for p in active)
        c=sorted(by[ts],key=lambda x:(x['family_rank'],x['family'],x['strike_key']))[0]
        if len(active)<a.max_positions and used+fixed<=a.initial_capital:
            active.append({**c,'position_value':fixed,'pnl':fixed*c['return']}); byfam[c['family']]+=fixed*c['return']
    positive_pnl=sum(v for v in byfam.values() if v>0); top_share=max(byfam.values(),default=0)/positive_pnl if positive_pnl else 0
    if top_share>.70:reasons.append('strict_holdout_family_concentration')

    result={'version':'v13','methodology':{'purpose':'strict chronological out-of-sample audit after V12','family_selection':'frozen from V6; no family/parameter selection is performed on the holdout','horizon_bars':a.horizon,'friction_bps':a.cost_bps+a.slippage_bps,'initial_capital':a.initial_capital,'allocation_pct':a.allocation_pct,'max_positions':a.max_positions,'holdout_pct':a.holdout_pct,'important_limitation':'Because V6 family discovery used the full historical dataset, V13 is a strict holdout of the frozen strategy, not a fully independent discovery experiment.'},'data_quality':{'option_bar_rows':total,'contract_identity_coverage':nonnull/total,'identity_note':'Synthetic rolling-series identity is complete after V3 cleanup but is not exact exchange expiry identity.'},'families':names,'pre_holdout_folds':reports,'strict_holdout':h,'gate_metrics':{'pre_holdout_populated_folds':len(populated),'pre_holdout_positive_fold_rate':len(positive)/len(populated) if populated else 0,'pre_holdout_worst_pf':worst_pf,'strict_holdout_pf':holdout_pf,'strict_holdout_trades':h['trades'],'strict_holdout_top_family_positive_pnl_share':top_share},'gate_reasons':reasons,'next_gate':not reasons,'promotion_status':'RESEARCH_ONLY_NO_PAPER_TRADING','elapsed_seconds':round(time.time()-start,2)}
    Path(a.out).write_text(json.dumps(result,indent=2))
    print(json.dumps({'families':len(names),'strict_holdout_trades':h['trades'],'strict_holdout_pf':holdout_pf,'strict_holdout_return':h['return_pct'],'pre_holdout_positive_fold_rate':result['gate_metrics']['pre_holdout_positive_fold_rate'],'pre_holdout_worst_pf':worst_pf,'next_gate':result['next_gate'],'out':a.out,'elapsed_seconds':result['elapsed_seconds']},indent=2),flush=True)

if __name__=='__main__':main()
