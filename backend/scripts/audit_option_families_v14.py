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
    for x in c:
        a=x*k20+a*(1-k20); b=x*k50+b*(1-k50); e20.append(a); e50.append(b)
    out=[]
    for i,r in enumerate(rows):
        prior=rows[max(0,i-20):i]; avg=sum(float(x.get('volume') or 0) for x in prior)/max(1,len(prior))
        close=float(r['close']); high=float(r.get('high') or close); low=float(r.get('low') or close)
        out.append({**r,'ema20':e20[i],'ema50':e50[i],'rel_volume':float(r.get('volume') or 0)/avg if avg else 0,'bar_range_pct':max(0,(high-low)/close) if close>0 else 0})
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

def build(rows,family,cond,horizon,base_friction,entry_delay,spread_bps,range_fraction):
    e=enrich(rows); out=[]
    for i in range(len(e)-horizon-entry_delay):
        r=e[i]
        if not signal(r,cond):continue
        j=i+entry_delay; x=i+horizon
        entry=float(e[j]['close']); exit_=float(e[x]['close'])
        if entry<=0 or exit_<0:continue
        # Conservative execution model: adverse spread on both sides plus a fraction of the
        # observed entry/exit bar range. This is a proxy, NOT actual bid/ask reconstruction.
        friction=base_friction + spread_bps/10000 + range_fraction*(e[j]['bar_range_pct']+e[x]['bar_range_pct'])
        ret=max(exit_/entry-1-friction,-1)
        out.append({'timestamp':r['timestamp'],'exit_timestamp':e[x]['timestamp'],'return':ret,'family':family,'strike_key':r['strike_key'],'entry_rel_volume':e[j]['rel_volume'],'entry_price':entry})
    return out

def simulate(events,initial,alloc,maxpos):
    by=defaultdict(list)
    for e in events:by[e['timestamp']].append(e)
    fixed=initial*alloc; cash=initial; active=[]; done=[]; skipped=0; maxexp=0; peak=initial; dd=0
    for ts in sorted(by):
        keep=[]
        for p in active:
            if p['exit_timestamp']<=ts: cash+=p['position_value']+p['pnl']; done.append(p)
            else: keep.append(p)
        active=keep; used=sum(p['position_value'] for p in active)
        c=sorted(by[ts],key=lambda x:(x['family'],x['strike_key']))[0]
        if len(active)>=maxpos or used+fixed>initial or cash<fixed: skipped+=1
        else:
            cash-=fixed; p={**c,'position_value':fixed,'pnl':fixed*c['return']}; active.append(p); used+=fixed; maxexp=max(maxexp,used/initial)
        equity=cash+sum(p['position_value']+p['pnl'] for p in active); peak=max(peak,equity); dd=min(dd,equity/peak-1 if peak else 0)
    for p in sorted(active,key=lambda x:x['exit_timestamp']): cash+=p['position_value']+p['pnl']; done.append(p)
    pnls=[p['pnl'] for p in done]; vals=[p['return'] for p in done]; wins=[x for x in pnls if x>0]; losses=[-x for x in pnls if x<0]
    pf=sum(wins)/sum(losses) if losses else (float('inf') if wins else None)
    return {'trades':len(done),'win_rate':len(wins)/len(done) if done else 0,'expectancy':statistics.mean(vals) if vals else 0,'profit_factor':pf,'return_pct':sum(pnls)/initial if initial else 0,'max_drawdown_pct':dd,'max_exposure_pct':maxexp,'skipped':skipped}

def main():
    p=argparse.ArgumentParser(description='V14 execution-realism audit using conservative cost, delay, range-slippage and liquidity stress proxies.')
    p.add_argument('--db',default='data/research/market_data.sqlite'); p.add_argument('--input',default='data/research/option_family_v6.json'); p.add_argument('--out',default='data/research/option_family_v14.json')
    p.add_argument('--horizon',type=int,default=6); p.add_argument('--cost-bps',type=float,default=5); p.add_argument('--slippage-bps',type=float,default=5); p.add_argument('--initial-capital',type=float,default=100000); p.add_argument('--allocation-pct',type=float,default=.02); p.add_argument('--max-positions',type=int,default=5); a=p.parse_args(); start=time.time()
    src=json.loads(Path(a.input).read_text()); fam=[r for r in src.get('results',[]) if r.get('eligible_for_next_research_gate')]
    if not fam:raise SystemExit('V14 requires V6 eligible families.')
    names=[r['family'] for r in fam]
    db=sqlite3.connect(a.db); db.row_factory=sqlite3.Row; cols=[r['name'] for r in db.execute('PRAGMA table_info(option_bars)')]
    required={'timestamp','side','strike_key','close','high','low','volume','oi','iv'}
    missing=required-set(cols)
    if missing: raise SystemExit(f'Missing required columns: {sorted(missing)}')
    total,nonnull=db.execute('SELECT COUNT(*),COUNT(contract_identity) FROM option_bars').fetchone() if 'contract_identity' in cols else (0,0)
    if total and nonnull!=total: raise SystemExit(f'V14 requires complete contract_identity coverage: {nonnull}/{total}')
    specs=sorted({(parse_name(n)[0],parse_name(n)[1]) for f in fam for n in f.get('matched_candidate_names',[])})
    groups={}
    for side,strike in specs:
        groups[(side,strike)]=[dict(r) for r in db.execute('SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp',(side,strike))]
    db.close()
    base=(a.cost_bps+a.slippage_bps)/10000
    scenarios=[
        {'name':'baseline_close','spread_bps':0,'range_fraction':0,'entry_delay':0,'min_rel_volume':0},
        {'name':'spread_10bps','spread_bps':10,'range_fraction':0,'entry_delay':0,'min_rel_volume':0},
        {'name':'spread_20bps','spread_bps':20,'range_fraction':0,'entry_delay':0,'min_rel_volume':0},
        {'name':'spread_30bps','spread_bps':30,'range_fraction':0,'entry_delay':0,'min_rel_volume':0},
        {'name':'range_10pct','spread_bps':10,'range_fraction':.10,'entry_delay':0,'min_rel_volume':0},
        {'name':'range_25pct','spread_bps':20,'range_fraction':.25,'entry_delay':0,'min_rel_volume':0},
        {'name':'one_bar_delay','spread_bps':10,'range_fraction':.10,'entry_delay':1,'min_rel_volume':0},
        {'name':'liquid_only_1x','spread_bps':20,'range_fraction':.10,'entry_delay':0,'min_rel_volume':1.0},
        {'name':'liquid_only_1_5x','spread_bps':20,'range_fraction':.10,'entry_delay':0,'min_rel_volume':1.5},
        {'name':'severe_execution','spread_bps':30,'range_fraction':.25,'entry_delay':1,'min_rel_volume':1.0},
    ]
    results=[]
    for s in scenarios:
        events=[]
        for f in fam:
            name=f['family']; side,cond=family_sig(name)
            for n in f.get('matched_candidate_names',[]):
                cs,strike,cc=parse_name(n)
                if cs!=side or cc!=cond: continue
                ev=build(groups.get((cs,strike),[]),name,cond,a.horizon,base,s['entry_delay'],s['spread_bps'],s['range_fraction'])
                if s['min_rel_volume']>0: ev=[e for e in ev if e['entry_rel_volume']>=s['min_rel_volume']]
                events.extend(ev)
        events.sort(key=lambda x:(x['timestamp'],x['family'],x['strike_key']))
        r=simulate(events,a.initial_capital,a.allocation_pct,a.max_positions); r.update({'scenario':s['name'],'spread_bps':s['spread_bps'],'range_fraction':s['range_fraction'],'entry_delay_bars':s['entry_delay'],'min_rel_volume':s['min_rel_volume']})
        results.append(r); print(f"OPTION FAMILY V14: {s['name']} trades={r['trades']} return={r['return_pct']:.2%} PF={r['profit_factor']} DD={r['max_drawdown_pct']:.2%} exposure={r['max_exposure_pct']:.2%} skipped={r['skipped']}",flush=True)
    byname={r['scenario']:r for r in results}; severe=byname['severe_execution']; liquid=byname['liquid_only_1_5x']; baseline=byname['baseline_close']
    reasons=[]
    for r in results:
        if r['trades']<200: reasons.append(f"low_trade_count:{r['scenario']}")
    if severe['profit_factor'] is None or severe['profit_factor']<1.05 or severe['return_pct']<=0: reasons.append('severe_execution_failure')
    if liquid['profit_factor'] is None or liquid['profit_factor']<1.10 or liquid['return_pct']<=0: reasons.append('liquidity_filtered_failure')
    if baseline['profit_factor'] is None or baseline['profit_factor']<1.10: reasons.append('baseline_failure')
    result={'version':'v14','methodology':{'purpose':'execution realism and liquidity stress after strict V13 OOS pass','base_friction_bps':a.cost_bps+a.slippage_bps,'allocation_pct':a.allocation_pct,'max_positions':a.max_positions,'horizon_bars':a.horizon,'execution_proxy_note':'No historical bid/ask quotes are present. Spread and range-fraction scenarios are conservative proxies, not reconstructed market microstructure. Exact brokerage, STT, exchange fees, lot-size history and contract-level fills require additional contract metadata.'},'data_quality':{'option_bar_rows':total,'contract_identity_coverage':nonnull/total if total else None,'bid_ask_available':False,'lot_size_history_available':False},'families':names,'scenarios':results,'gate_metrics':{'baseline_pf':baseline['profit_factor'],'severe_pf':severe['profit_factor'],'severe_return_pct':severe['return_pct'],'liquid_1_5x_pf':liquid['profit_factor'],'liquid_1_5x_return_pct':liquid['return_pct']},'gate_reasons':sorted(set(reasons)),'next_gate':not reasons,'promotion_status':'RESEARCH_ONLY_NO_PAPER_TRADING','elapsed_seconds':round(time.time()-start,2)}
    Path(a.out).write_text(json.dumps(result,indent=2)); print(json.dumps({'families':len(names),'baseline_pf':baseline['profit_factor'],'severe_pf':severe['profit_factor'],'liquid_1_5x_pf':liquid['profit_factor'],'gate_reasons':sorted(set(reasons)),'next_gate':result['next_gate'],'out':a.out,'elapsed_seconds':result['elapsed_seconds']},indent=2),flush=True)

if __name__=='__main__':main()
