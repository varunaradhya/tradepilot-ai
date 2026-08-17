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
        prior=rows[max(0,i-20):i]; avg=sum(float(x.get('volume') or 0) for x in prior)/max(1,len(prior))
        out.append({**r,'ema20':e20[i],'ema50':e50[i],'rel_volume':float(r.get('volume') or 0)/avg if avg else 0})
    return out


def signal(r,cond):
    for c in cond:
        if c=='premium_trend' and not r['ema20']>r['ema50']: return False
        if c=='premium_weak' and not r['ema20']<r['ema50']: return False
        if c=='relvol_1_5' and not r['rel_volume']>=1.5: return False
        if c=='iv_high' and not float(r.get('iv') or 0)>20: return False
        if c=='iv_low' and not (0<float(r.get('iv') or 0)<15): return False
        if c=='oi_present' and not float(r.get('oi') or 0)>0: return False
    return True


def build(rows,family,cond,horizon,friction,rank):
    e=enrich(rows); out=[]
    for i in range(len(e)-horizon):
        r=e[i]
        if not signal(r,cond): continue
        entry=float(r['close']); exit_=float(e[i+horizon]['close'])
        if entry<=0 or exit_<0: continue
        out.append({'timestamp':r['timestamp'],'exit_timestamp':e[i+horizon]['timestamp'],'return':max(exit_/entry-1-friction,-1),'family':family,'family_rank':rank,'strike_key':r['strike_key']})
    return out


def simulate(events,initial,alloc,maxpos):
    by=defaultdict(list)
    for e in events: by[e['timestamp']].append(e)
    fixed=initial*alloc; cash=initial; active=[]; done=[]; skipped=0; maxexp=0; peak=initial; dd=0
    for ts in sorted(by):
        keep=[]
        for p in active:
            if p['exit_timestamp']<=ts:
                cash+=p['position_value']+p['pnl']; done.append(p)
            else: keep.append(p)
        active=keep; used=sum(p['position_value'] for p in active)
        if by[ts]:
            c=sorted(by[ts],key=lambda x:(x['family_rank'],x['family'],x['strike_key']))[0]
            if len(active)>=maxpos or used+fixed>initial or cash<fixed:
                skipped+=1
            else:
                cash-=fixed; p={**c,'position_value':fixed,'pnl':fixed*c['return']}; active.append(p); used+=fixed; maxexp=max(maxexp,used/initial)
        equity=cash+sum(p['position_value']+p['pnl'] for p in active); peak=max(peak,equity); dd=min(dd,equity/peak-1 if peak else 0)
    for p in sorted(active,key=lambda x:x['exit_timestamp']): cash+=p['position_value']+p['pnl']; done.append(p)
    pnls=[p['pnl'] for p in done]; vals=[p['return'] for p in done]; wins=[x for x in pnls if x>0]; losses=[-x for x in pnls if x<0]
    pf=sum(wins)/sum(losses) if losses else (float('inf') if wins else None)
    return {'trades':len(done),'win_rate':len(wins)/len(done) if done else 0,'expectancy':statistics.mean(vals) if vals else 0,'profit_factor':pf,'return_pct':sum(pnls)/initial if initial else 0,'max_drawdown_pct':dd,'max_exposure_pct':maxexp,'skipped':skipped}


def build_events(groups,fam,horizon,friction,rank):
    events=[]
    for f in fam:
        name=f['family']; side,cond=family_sig(name)
        for n in f.get('matched_candidate_names',[]):
            cs,strike,cc=parse_name(n)
            if cs==side and cc==cond:
                events.extend(build(groups.get((cs,strike),[]),name,cond,horizon,friction,rank[name]))
    return sorted(events,key=lambda x:(x['timestamp'],x['family_rank'],x['strike_key']))


def run_case(events,initial,alloc,maxpos):
    return simulate(events,initial,alloc,maxpos)


def main():
    p=argparse.ArgumentParser(description='V12 robustness, ablation and anti-overfitting audit after V11.')
    p.add_argument('--db',default='data/research/market_data.sqlite'); p.add_argument('--input',default='data/research/option_family_v6.json'); p.add_argument('--out',default='data/research/option_family_v12.json')
    p.add_argument('--horizon',type=int,default=6); p.add_argument('--cost-bps',type=float,default=5); p.add_argument('--slippage-bps',type=float,default=5); p.add_argument('--initial-capital',type=float,default=100000); p.add_argument('--allocation-pct',type=float,default=.02); p.add_argument('--max-positions',type=int,default=5)
    a=p.parse_args(); start=time.time()
    src=json.loads(Path(a.input).read_text()); fam=[r for r in src.get('results',[]) if r.get('eligible_for_next_research_gate')]
    if not fam: raise SystemExit('V12 requires V6 eligible families.')
    names=[r['family'] for r in fam]; rank={n:i for i,n in enumerate(names)}
    db=sqlite3.connect(a.db); db.row_factory=sqlite3.Row
    cols=[r['name'] for r in db.execute('PRAGMA table_info(option_bars)')]
    if 'contract_identity' not in cols: raise SystemExit('V12 requires contract_identity column.')
    total,nonnull=db.execute('SELECT COUNT(*),COUNT(contract_identity) FROM option_bars').fetchone()
    if total==0 or nonnull!=total: raise SystemExit(f'V12 requires complete contract_identity coverage: {nonnull}/{total}')
    specs=sorted({(parse_name(n)[0],parse_name(n)[1]) for f in fam for n in f.get('matched_candidate_names',[])})
    groups={}
    for side,strike in specs:
        groups[(side,strike)]=[dict(r) for r in db.execute('SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp',(side,strike))]
    db.close()

    costs=[10,15,20,30,50]
    horizons=[3,6,12,24]
    stress=[]
    for bps in costs:
        ev=build_events(groups,fam,a.horizon,bps/10000,rank); r=run_case(ev,a.initial_capital,a.allocation_pct,a.max_positions)
        stress.append({'cost_bps_total':bps,'trades':r['trades'],'expectancy':r['expectancy'],'profit_factor':r['profit_factor'],'return_pct':r['return_pct'],'max_drawdown_pct':r['max_drawdown_pct']})
        print(f"OPTION FAMILY V12: cost={bps}bps trades={r['trades']} return={r['return_pct']:.2%} PF={r['profit_factor']} DD={r['max_drawdown_pct']:.2%}",flush=True)

    horizon_results=[]
    for h in horizons:
        ev=build_events(groups,fam,h,(a.cost_bps+a.slippage_bps)/10000,rank); r=run_case(ev,a.initial_capital,a.allocation_pct,a.max_positions)
        horizon_results.append({'horizon_bars':h,'trades':r['trades'],'expectancy':r['expectancy'],'profit_factor':r['profit_factor'],'return_pct':r['return_pct'],'max_drawdown_pct':r['max_drawdown_pct']})
        print(f"OPTION FAMILY V12: horizon={h} trades={r['trades']} return={r['return_pct']:.2%} PF={r['profit_factor']} DD={r['max_drawdown_pct']:.2%}",flush=True)

    allocation_results=[]; ev_base=build_events(groups,fam,a.horizon,(a.cost_bps+a.slippage_bps)/10000,rank); base_result=run_case(ev_base,a.initial_capital,a.allocation_pct,a.max_positions)
    for alloc in (.005,.01,.02,.05):
        r=run_case(ev_base,a.initial_capital,alloc,a.max_positions)
        allocation_results.append({'allocation_pct':alloc,'trades':r['trades'],'return_pct':r['return_pct'],'profit_factor':r['profit_factor'],'max_drawdown_pct':r['max_drawdown_pct'],'max_exposure_pct':r['max_exposure_pct']})
        print(f"OPTION FAMILY V12: alloc={alloc:.1%} trades={r['trades']} return={r['return_pct']:.2%} PF={r['profit_factor']} DD={r['max_drawdown_pct']:.2%} exposure={r['max_exposure_pct']:.2%}",flush=True)

    ablation=[]
    for removed in names:
        subset=[f for f in fam if f['family']!=removed]; subrank={n:i for i,n in enumerate([f['family'] for f in subset])}
        ev=build_events(groups,subset,a.horizon,(a.cost_bps+a.slippage_bps)/10000,subrank); r=run_case(ev,a.initial_capital,a.allocation_pct,a.max_positions)
        ablation.append({'removed_family':removed,'trades':r['trades'],'expectancy':r['expectancy'],'profit_factor':r['profit_factor'],'return_pct':r['return_pct'],'max_drawdown_pct':r['max_drawdown_pct']})
        print(f"OPTION FAMILY V12: ablation remove={removed} trades={r['trades']} return={r['return_pct']:.2%} PF={r['profit_factor']} DD={r['max_drawdown_pct']:.2%}",flush=True)

    strikes=sorted({parse_name(n)[1] for f in fam for n in f.get('matched_candidate_names',[])}); strike_ablation=[]
    for strike in strikes:
        filtered={k:v for k,v in groups.items() if k[1]!=strike}; ev=build_events(filtered,fam,a.horizon,(a.cost_bps+a.slippage_bps)/10000,rank); r=run_case(ev,a.initial_capital,a.allocation_pct,a.max_positions)
        strike_ablation.append({'removed_strike_key':strike,'trades':r['trades'],'expectancy':r['expectancy'],'profit_factor':r['profit_factor'],'return_pct':r['return_pct'],'max_drawdown_pct':r['max_drawdown_pct']})
        print(f"OPTION FAMILY V12: strike_ablation remove={strike} trades={r['trades']} return={r['return_pct']:.2%} PF={r['profit_factor']} DD={r['max_drawdown_pct']:.2%}",flush=True)

    placebo=[]
    if ev_base:
        returns=[e['return'] for e in ev_base]; shift=max(1,len(returns)//7); shuffled=[{**e,'return':returns[(i+shift)%len(returns)]} for i,e in enumerate(ev_base)]
        r=run_case(shuffled,a.initial_capital,a.allocation_pct,a.max_positions)
        placebo.append({'method':'deterministic_return_rotation','shift':shift,'trades':r['trades'],'expectancy':r['expectancy'],'profit_factor':r['profit_factor'],'return_pct':r['return_pct'],'max_drawdown_pct':r['max_drawdown_pct']})
        print(f"OPTION FAMILY V12: placebo rotation trades={r['trades']} return={r['return_pct']:.2%} PF={r['profit_factor']} DD={r['max_drawdown_pct']:.2%}",flush=True)

    stress_pass=all((x['profit_factor'] is not None and x['profit_factor']>=1.10 and x['expectancy']>0) for x in stress)
    horizon_positive=sum(1 for x in horizon_results if x['expectancy']>0 and x['profit_factor'] is not None and x['profit_factor']>=1.05)
    ablation_pass=sum(1 for x in ablation if x['profit_factor'] is not None and x['profit_factor']>=1.10 and x['expectancy']>0)
    strike_pass=sum(1 for x in strike_ablation if x['profit_factor'] is not None and x['profit_factor']>=1.10 and x['expectancy']>0)
    placebo_pf=placebo[0]['profit_factor'] if placebo else None
    placebo_expectancy=placebo[0]['expectancy'] if placebo else None
    base_expectancy=base_result['expectancy']
    placebo_gap=base_expectancy-placebo_expectancy if placebo else None
    reasons=[]
    if not stress_pass: reasons.append('cost_stress_failure')
    if horizon_positive<3: reasons.append('horizon_robustness_failure')
    if ablation_pass<len(ablation)-1: reasons.append('family_ablation_failure')
    if strike_pass<max(1,len(strike_ablation)-2): reasons.append('strike_ablation_failure')
    if placebo and placebo_pf is not None and placebo_pf>=1.10 and placebo_expectancy>=base_expectancy: reasons.append('placebo_not_beaten')
    result={'version':'v12','methodology':{'purpose':'robustness, ablation and anti-overfitting audit after chronological V11','base_horizon_bars':a.horizon,'base_friction_bps':a.cost_bps+a.slippage_bps,'initial_capital':a.initial_capital,'allocation_pct':a.allocation_pct,'max_positions':a.max_positions,'important_limitation':'Family selection remains inherited from V6; this is not a clean independent OOS discovery process.'},'data_quality':{'option_bar_rows':total,'contract_identity_coverage':nonnull/total,'identity_note':'Rows have complete rolling-series identity coverage after V3 cleanup; identity is synthetic rolling-series identity, not exact exchange contract expiry identity.'},'families':names,'cost_stress':stress,'horizon_robustness':horizon_results,'allocation_sensitivity':allocation_results,'family_ablation':ablation,'strike_ablation':strike_ablation,'placebo':placebo,'gate_metrics':{'cost_stress_pass':stress_pass,'positive_horizons_ge_pf105':horizon_positive,'family_ablation_pass_count':ablation_pass,'strike_ablation_pass_count':strike_pass,'base_expectancy':base_expectancy,'placebo_profit_factor':placebo_pf,'placebo_expectancy':placebo_expectancy,'placebo_expectancy_gap_vs_base':placebo_gap},'gate_reasons':reasons,'next_gate':not reasons,'promotion_status':'RESEARCH_ONLY_NO_PAPER_TRADING','elapsed_seconds':round(time.time()-start,2)}
    Path(a.out).write_text(json.dumps(result,indent=2)); print(json.dumps({'families':len(names),'cost_stress_pass':stress_pass,'positive_horizons_ge_pf105':horizon_positive,'family_ablation_pass_count':ablation_pass,'strike_ablation_pass_count':strike_pass,'base_expectancy':base_expectancy,'placebo_profit_factor':placebo_pf,'placebo_expectancy_gap_vs_base':placebo_gap,'next_gate':result['next_gate'],'out':a.out,'elapsed_seconds':result['elapsed_seconds']},indent=2),flush=True)

if __name__=='__main__': main()
