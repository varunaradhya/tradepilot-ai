from __future__ import annotations
import argparse, json, sqlite3, statistics, time
from collections import defaultdict
from pathlib import Path


def args():
    p=argparse.ArgumentParser(description='V9 capital-aware option family portfolio audit')
    p.add_argument('--db',default='data/research/market_data.sqlite'); p.add_argument('--input',default='data/research/option_family_v6.json'); p.add_argument('--out',default='data/research/option_family_v9.json')
    p.add_argument('--horizon',type=int,default=6); p.add_argument('--cost-bps',type=float,default=5); p.add_argument('--slippage-bps',type=float,default=5)
    p.add_argument('--initial-capital',type=float,default=100000.0); p.add_argument('--allocation-pct',type=float,default=0.02); p.add_argument('--max-positions',type=int,default=5); p.add_argument('--min-trades',type=int,default=100)
    return p.parse_args()


def parse_name(n):
    p=n.split(':'); side=p[0]; strike=p[1] if len(p)>1 else ''; cond=tuple(sorted(x for x in (p[2].split('+') if len(p)>2 else []) if x)); return side,strike,cond


def family_sig(n):
    p=n.split(':'); side=p[0]; raw=p[2].split('+') if len(p)>=3 else (p[1].split('+') if len(p)==2 else []); return side,tuple(sorted(x for x in raw if x and x!='base'))


def enrich(rows):
    rows=sorted(rows,key=lambda r:r['timestamp'])
    if not rows:return []
    c=[float(r['close']) for r in rows]; k20,k50=2/21,2/51; a=b=c[0]; e20=[]; e50=[]
    for x in c:a=x*k20+a*(1-k20); b=x*k50+b*(1-k50); e20.append(a); e50.append(b)
    out=[]
    for i,r in enumerate(rows):
        prior=rows[max(0,i-20):i]; avg=sum(float(x.get('volume') or 0) for x in prior)/max(len(prior),1)
        out.append({**r,'ema20':e20[i],'ema50':e50[i],'rel_volume':float(r.get('volume') or 0)/avg if avg else 0.0})
    return out


def signal(r,cond):
    for c in cond:
        if c=='premium_trend' and not r['ema20']>r['ema50']:return False
        if c=='premium_weak' and not r['ema20']<r['ema50']:return False
        if c=='relvol_1_5' and not r['rel_volume']>=1.5:return False
        if c=='iv_high' and not float(r.get('iv') or 0)>20:return False
        if c=='iv_low' and not 0<float(r.get('iv') or 0)<15:return False
        if c=='oi_present' and not float(r.get('oi') or 0)>0:return False
    return True


def build(rows,family,cond,horizon,friction,rank):
    e=enrich(rows); out=[]
    for i in range(len(e)-horizon):
        r=e[i]
        if not signal(r,cond):continue
        entry=float(r['close']); exit_price=float(e[i+horizon]['close'])
        if entry<=0 or exit_price<0:continue
        ret=max(exit_price/entry-1-friction,-1.0)
        out.append({'timestamp':r['timestamp'],'exit_timestamp':e[i+horizon]['timestamp'],'return':ret,'family':family,'family_rank':rank,'strike_key':r['strike_key']})
    return out


def drawdown(curve):
    if not curve:return 0.0
    peak=curve[0]; worst=0.0
    for x in curve:
        peak=max(peak,x)
        if peak>0:worst=min(worst,x/peak-1)
    return worst


def stats(trades,initial_capital):
    if not trades:return {'trades':0,'wins':0,'win_rate':0,'expectancy_return':0,'profit_factor':None,'pnl':0,'final_capital':initial_capital,'total_return_pct':0,'max_drawdown_pct':0,'average_position_pnl':0}
    vals=[t['return'] for t in trades]; pnls=[t['pnl'] for t in trades]; wins=[x for x in pnls if x>0]; losses=[-x for x in pnls if x<0]; value=initial_capital; curve=[]
    for t in sorted(trades,key=lambda x:x['exit_timestamp']):value+=t['pnl']; curve.append(value)
    pf=sum(wins)/sum(losses) if losses else (float('inf') if wins else None); total=sum(pnls)
    return {'trades':len(trades),'wins':len(wins),'win_rate':len(wins)/len(trades),'expectancy_return':statistics.mean(vals),'profit_factor':pf,'pnl':total,'final_capital':initial_capital+total,'total_return_pct':total/initial_capital if initial_capital>0 else 0.0,'max_drawdown_pct':drawdown(curve),'average_position_pnl':statistics.mean(pnls)}


def choose(candidates,policy):
    if not candidates:return []
    ordered=sorted(candidates,key=lambda x:(x['family_rank'],x['family'],x['strike_key']))
    if policy=='all_available':return ordered
    if policy=='top_family_per_timestamp':return ordered[:1]
    if policy=='one_per_family':
        unique={}
        for c in ordered:unique.setdefault(c['family'],c)
        return list(unique.values())
    return ordered


def simulate(events,initial_capital,alloc,maxpos,policy):
    by=defaultdict(list)
    for e in events:by[e['timestamp']].append(e)
    cash=initial_capital; active=[]; executed=[]; skipped=0; family_pnl=defaultdict(float); maxactive=0; max_exposure=0.0; stop_reason=None
    for ts in sorted(by):
        keep=[]
        for pos in active:
            if pos['exit_timestamp']<=ts:
                cash+=pos['position_value']+pos['pnl']; executed.append(pos); family_pnl[pos['family']]+=pos['pnl']
            else:keep.append(pos)
        active=keep
        if cash<=0 and not active:
            stop_reason='capital_exhausted'; skipped+=sum(len(by[t]) for t in sorted(by) if t>=ts); break
        candidates=choose(by[ts],policy); available_equity=cash+sum(p['position_value'] for p in active)
        for c in candidates:
            if len(active)>=maxpos or available_equity<=0 or cash<=0:
                skipped+=1; continue
            pv=min(available_equity*alloc,cash)
            if pv<=0:skipped+=1; continue
            cash-=pv
            pos={**c,'entry_capital':available_equity,'position_value':pv,'pnl':pv*c['return']}
            active.append(pos); available_equity=cash+sum(p['position_value'] for p in active); maxactive=max(maxactive,len(active)); max_exposure=max(max_exposure,sum(p['position_value'] for p in active)/max(available_equity,1e-12))
    for pos in sorted(active,key=lambda x:x['exit_timestamp']):cash+=pos['position_value']+pos['pnl']; executed.append(pos); family_pnl[pos['family']]+=pos['pnl']
    r=stats(executed,initial_capital); r.update({'policy':policy,'allocation_pct':alloc,'max_positions':maxpos,'max_simultaneous_positions':maxactive,'skipped_signals':skipped,'capital_utilization_limit_pct':alloc*maxpos,'max_observed_exposure_pct':max_exposure,'ending_cash':cash,'family_pnl':dict(sorted(family_pnl.items(),key=lambda x:x[1],reverse=True)),'stop_reason':stop_reason}); return r


def gate(r,mintrades):return r['trades']>=mintrades and r['total_return_pct']>0 and r['profit_factor'] is not None and r['profit_factor']>=1.10 and r['max_drawdown_pct']>-0.30 and r['skipped_signals']<r['trades']*2


def main():
    a=args(); start=time.time(); src=json.loads(Path(a.input).read_text(encoding='utf-8')); fam=[r for r in src.get('results',[]) if r.get('eligible_for_next_research_gate')]
    if not fam:raise SystemExit('V9 requires V6 eligible families.')
    v7p=Path(a.input).with_name('option_family_v7.json'); scores={}
    if v7p.exists():
        try:
            v7=json.loads(v7p.read_text(encoding='utf-8')); rows=v7.get('results',v7.get('families',[]));
            if isinstance(rows,list):scores={r.get('family'):i for i,r in enumerate(rows) if r.get('family')}
        except Exception:pass
    names=sorted([f['family'] for f in fam],key=lambda n:scores.get(n,999)); rank={n:i for i,n in enumerate(names)}; print(f'OPTION FAMILY V9: eligible families={len(fam)} {names}',flush=True)
    specs=sorted({(parse_name(n)[0],parse_name(n)[1]) for f in fam for n in f.get('matched_candidate_names',[])}); db=sqlite3.connect(a.db); db.row_factory=sqlite3.Row; groups={}
    try:
        for i,(side,strike) in enumerate(specs,1):
            print(f'OPTION FAMILY V9: loading option group {i}/{len(specs)} {side}:{strike}',flush=True)
            groups[(side,strike)]=[dict(r) for r in db.execute('SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp',(side,strike))]
    finally:db.close()
    friction=(a.cost_bps+a.slippage_bps)/10000; events=[]; counts=defaultdict(int)
    for f in fam:
        name=f['family']; side,cond=family_sig(name)
        for candidate in f.get('matched_candidate_names',[]):
            cs,strike,cc=parse_name(candidate)
            if cs==side and cc==cond:
                built=build(groups.get((cs,strike),[]),name,cond,a.horizon,friction,rank[name]); events.extend(built); counts[name]+=len(built)
    events.sort(key=lambda x:(x['timestamp'],x['family_rank'],x['strike_key'])); print(f'OPTION FAMILY V9: raw_events={len(events)}',flush=True)
    reports=[]
    for policy in ('all_available','one_per_family','top_family_per_timestamp'):
        for alloc in (.01,.02,.05):
            for maxpos in (1,3,5,10):
                r=simulate(events,a.initial_capital,alloc,maxpos,policy); reports.append(r); print(f"OPTION FAMILY V9: policy={policy} alloc={alloc:.0%} maxpos={maxpos} trades={r['trades']} final={r['final_capital']:.2f} return={r['total_return_pct']:.4%} PF={r['profit_factor']} DD={r['max_drawdown_pct']:.2%} skipped={r['skipped_signals']} exposure={r['max_observed_exposure_pct']:.2%}",flush=True)
    default=next(r for r in reports if r['policy']=='top_family_per_timestamp' and r['allocation_pct']==a.allocation_pct and r['max_positions']==a.max_positions); best=max((r for r in reports if r['trades']>=a.min_trades),key=lambda r:r['total_return_pct'],default=default); ng=gate(default,a.min_trades)
    result={'version':'v9','methodology':{'horizon_bars':a.horizon,'friction_bps':a.cost_bps+a.slippage_bps,'initial_capital':a.initial_capital,'position_allocation_pct':a.allocation_pct,'max_simultaneous_positions':a.max_positions,'position_sizing':'percentage of current equity at entry; cash is reserved until exit; no leverage','overlap_policy_default':'top_family_per_timestamp','selection_rule':'V7 research rank only; no future-return selection','return_model':'capital-aware cash/equity accounting with reserved position capital'},'eligible_families':names,'raw_events':len(events),'family_event_counts':dict(counts),'default_simulation':default,'best_grid_result_by_total_return':best,'grid_results':reports,'next_gate':ng,'promotion_status':'RESEARCH_ONLY_NO_PAPER_TRADING','critical_limits':['Historical contract/expiry identity remains unvalidated.','Bid-ask spreads, fills, lot size and liquidity are not modeled beyond configured friction.','Existing option cache may contain rolling/synthetic continuity.','Extreme historical option repricing remains a data-quality risk and must be audited before promotion.'],'elapsed_seconds':round(time.time()-start,2)}
    Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'families':len(fam),'raw_events':len(events),'default_trades':default['trades'],'default_final_capital':default['final_capital'],'default_return_pct':default['total_return_pct'],'default_profit_factor':default['profit_factor'],'default_max_drawdown_pct':default['max_drawdown_pct'],'default_max_exposure_pct':default['max_observed_exposure_pct'],'next_gate':ng,'out':a.out,'elapsed_seconds':result['elapsed_seconds']},indent=2),flush=True)

if __name__=='__main__':main()
