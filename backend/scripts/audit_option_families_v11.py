from __future__ import annotations
import argparse, json, sqlite3, statistics, time
from collections import defaultdict
from pathlib import Path

def args():
    p=argparse.ArgumentParser(description='V11 exact option contract/expiry integrity and fixed-notional portfolio audit')
    p.add_argument('--db',default='data/research/market_data.sqlite'); p.add_argument('--input',default='data/research/option_family_v6.json'); p.add_argument('--out',default='data/research/option_family_v11.json')
    p.add_argument('--horizon',type=int,default=6); p.add_argument('--cost-bps',type=float,default=5); p.add_argument('--slippage-bps',type=float,default=5)
    p.add_argument('--initial-capital',type=float,default=100000); p.add_argument('--allocation-pct',type=float,default=.02); p.add_argument('--max-positions',type=int,default=5); p.add_argument('--min-trades',type=int,default=100)
    return p.parse_args()

def parse_name(n):
    p=n.split(':'); side=p[0]; strike=p[1] if len(p)>1 else ''; cond=tuple(sorted(x for x in (p[2].split('+') if len(p)>2 else []) if x)); return side,strike,cond

def family_sig(n):
    p=n.split(':'); side=p[0]; raw=p[2].split('+') if len(p)>=3 else (p[1].split('+') if len(p)==2 else []); return side,tuple(sorted(x for x in raw if x and x!='base'))

def enrich(rows):
    rows=sorted(rows,key=lambda r:r['timestamp']); c=[float(r['close']) for r in rows]; a=b=c[0] if c else 0; k20,k50=2/21,2/51; e20=[]; e50=[]
    for x in c: a=x*k20+a*(1-k20); b=x*k50+b*(1-k50); e20.append(a); e50.append(b)
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
        if c=='iv_low' and not 0<float(r.get('iv') or 0)<15: return False
        if c=='oi_present' and not float(r.get('oi') or 0)>0: return False
    return True

def build(rows,family,cond,horizon,friction,rank):
    e=enrich(rows); out=[]
    for i in range(len(e)-horizon):
        r=e[i]
        if not signal(r,cond): continue
        entry=float(r['close']); exit_price=float(e[i+horizon]['close'])
        if entry<=0 or exit_price<0 or not r.get('expiry') or not r.get('contract_identity'): continue
        ret=max(exit_price/entry-1-friction,-1.0)
        out.append({'timestamp':r['timestamp'],'exit_timestamp':e[i+horizon]['timestamp'],'return':ret,'family':family,'family_rank':rank,'strike_key':r['strike_key'],'expiry':r['expiry'],'contract_identity':r['contract_identity']})
    return out

def stats(trades,initial):
    if not trades: return {'trades':0,'win_rate':0,'expectancy':0,'profit_factor':None,'final_capital':initial,'return_pct':0,'max_drawdown_pct':0}
    pnls=[t['pnl'] for t in trades]; wins=[x for x in pnls if x>0]; losses=[-x for x in pnls if x<0]; value=initial; peak=initial; dd=0
    for t in sorted(trades,key=lambda x:x['exit_timestamp']):
        value+=t['pnl']; peak=max(peak,value); dd=min(dd,value/peak-1)
    pf=sum(wins)/sum(losses) if losses else float('inf')
    return {'trades':len(trades),'win_rate':len(wins)/len(trades),'expectancy':statistics.mean([t['return'] for t in trades]),'profit_factor':pf,'final_capital':value,'return_pct':value/initial-1,'max_drawdown_pct':dd}

def simulate(events,initial,alloc,maxpos):
    by=defaultdict(list)
    for e in events: by[e['timestamp']].append(e)
    fixed=initial*alloc; active=[]; executed=[]; skipped=0; cash=initial; maxexp=0
    for ts in sorted(by):
        keep=[]
        for p in active:
            if p['exit_timestamp']<=ts: cash+=p['position_value']+p['pnl']; executed.append(p)
            else: keep.append(p)
        active=keep; candidates=sorted(by[ts],key=lambda x:(x['family_rank'],x['family'],x['strike_key'],str(x['expiry']),str(x['contract_identity'])))[:1]
        used=sum(p['position_value'] for p in active)
        for c in candidates:
            if len(active)>=maxpos or used+fixed>initial or cash<fixed: skipped+=1; continue
            cash-=fixed; p={**c,'position_value':fixed,'pnl':fixed*c['return']}; active.append(p); used+=fixed; maxexp=max(maxexp,used/initial)
    for p in sorted(active,key=lambda x:x['exit_timestamp']): cash+=p['position_value']+p['pnl']; executed.append(p)
    r=stats(executed,initial); r.update({'skipped':skipped,'max_exposure_pct':maxexp,'allocation_pct':alloc,'max_positions':maxpos}); return r

def main():
    a=args(); start=time.time(); src=json.loads(Path(a.input).read_text(encoding='utf-8')); fam=[r for r in src.get('results',[]) if r.get('eligible_for_next_research_gate')]
    if not fam: raise SystemExit('V11 requires V6 eligible families.')
    names=[f['family'] for f in fam]; rank={n:i for i,n in enumerate(names)}; print(f'OPTION FAMILY V11: eligible families={len(names)} {names}',flush=True)
    con=sqlite3.connect(a.db); con.row_factory=sqlite3.Row
    cols=[r['name'] for r in con.execute('PRAGMA table_info(option_bars)')]
    required={'expiry','contract_identity'}; missing=sorted(required-set(cols));
    if missing:
        result={'version':'v11','status':'BLOCKED_SCHEMA','missing_columns':missing,'next_gate':False,'gate_reasons':['missing_contract_or_expiry_identity_column'],'out':a.out}; Path(a.out).write_text(json.dumps(result,indent=2),encoding='utf-8'); con.close(); print(json.dumps(result,indent=2)); return
    q='SELECT COUNT(*) total, SUM(CASE WHEN expiry IS NOT NULL AND TRIM(expiry)<>"" AND contract_identity IS NOT NULL AND TRIM(contract_identity)<>"" THEN 1 ELSE 0 END) identified, COUNT(DISTINCT contract_identity) contracts, COUNT(DISTINCT expiry) expiries FROM option_bars'
    total,identified,contracts,expiries=con.execute(q).fetchone(); coverage=identified/total if total else 0
    duplicate=con.execute('''SELECT COUNT(*) FROM (SELECT timestamp,side,strike_key,expiry,contract_identity,COUNT(*) n FROM option_bars GROUP BY 1,2,3,4,5 HAVING n>1)''').fetchone()[0]
    print(f'OPTION FAMILY V11: rows={total} identified={identified} coverage={coverage:.2%} contracts={contracts} expiries={expiries} duplicate_identity_groups={duplicate}',flush=True)
    specs=sorted({(parse_name(n)[0],parse_name(n)[1]) for f in fam for n in f.get('matched_candidate_names',[])})
    groups={}
    for side,strike in specs:
        print(f'OPTION FAMILY V11: loading {side}:{strike}',flush=True)
        groups[(side,strike)]=[dict(r) for r in con.execute('SELECT timestamp,side,strike_key,strike,expiry,contract_identity,open,high,low,close,volume,oi,iv,spot FROM option_bars WHERE side=? AND strike_key=? AND expiry IS NOT NULL AND contract_identity IS NOT NULL ORDER BY timestamp',(side,strike))]
    con.close()
    friction=(a.cost_bps+a.slippage_bps)/10000; events=[]; family_counts=defaultdict(int)
    for f in fam:
        name=f['family']; side,cond=family_sig(name)
        for candidate in f.get('matched_candidate_names',[]):
            cs,strike,cc=parse_name(candidate)
            if cs==side and cc==cond:
                built=build(groups.get((cs,strike),[]),name,cond,a.horizon,friction,rank[name]); events.extend(built); family_counts[name]+=len(built)
    events.sort(key=lambda x:(x['timestamp'],x['family_rank'],x['strike_key']))
    r=simulate(events,a.initial_capital,a.allocation_pct,a.max_positions)
    reasons=[]
    if coverage<1: reasons.append('incomplete_contract_identity_coverage')
    if duplicate: reasons.append('duplicate_contract_identity_groups')
    if r['trades']<a.min_trades: reasons.append('insufficient_exact_contract_trades')
    if r['profit_factor'] is None or r['profit_factor']<1.10: reasons.append('weak_profit_factor')
    if r['return_pct']<=0: reasons.append('non_positive_return')
    if r['max_drawdown_pct']<=-0.30: reasons.append('excessive_drawdown')
    result={'version':'v11','methodology':{'contract_lock':'exact expiry + contract_identity','horizon_bars':a.horizon,'friction_bps':a.cost_bps+a.slippage_bps,'initial_capital':a.initial_capital,'allocation_pct':a.allocation_pct,'max_positions':a.max_positions,'selection':'top family rank per timestamp only'},'data_quality':{'option_bars_columns':cols,'rows':total,'identified_rows':identified,'identity_coverage':coverage,'distinct_contracts':contracts,'distinct_expiries':expiries,'duplicate_identity_groups':duplicate},'families':names,'family_event_counts':dict(family_counts),'exact_contract_events':len(events),'default_simulation':r,'gate_reasons':reasons,'next_gate':not reasons,'promotion_status':'RESEARCH_ONLY_NO_PAPER_TRADING','out':a.out,'elapsed_seconds':round(time.time()-start,2)}
    Path(a.out).write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'exact_contract_events':len(events),'default_trades':r['trades'],'final_capital':r['final_capital'],'return_pct':r['return_pct'],'profit_factor':r['profit_factor'],'max_drawdown_pct':r['max_drawdown_pct'],'gate_reasons':reasons,'next_gate':not reasons,'out':a.out},indent=2),flush=True)

if __name__=='__main__': main()
