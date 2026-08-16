from __future__ import annotations

import argparse, json, math, sqlite3, time
from collections import defaultdict


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument('--db',default='data/research/market_data.sqlite')
    p.add_argument('--input',default='data/research/option_family_v6.json')
    p.add_argument('--out',default='data/research/option_family_v7.json')
    p.add_argument('--horizon',type=int,default=6)
    p.add_argument('--cost-bps',type=float,default=5)
    p.add_argument('--slippage-bps',type=float,default=5)
    return p.parse_args()


def family_name(x):
    return x.get('family') or x.get('name') or ''


def main():
    a=parse_args(); t=time.time()
    with open(a.input,encoding='utf-8') as f: src=json.load(f)
    fams=[x for x in src.get('families',[]) if x.get('eligible')]
    names=[family_name(x) for x in fams]
    print(f'OPTION FAMILY V7: V6 eligible families={len(fams)} {names}',flush=True)

    con=sqlite3.connect(a.db); con.row_factory=sqlite3.Row
    # Discover the actual option table/columns without assuming a fixed schema.
    tables=[r[0] for r in con.execute("select name from sqlite_master where type='table'")]
    candidates=[t for t in tables if 'option' in t.lower()]
    print(f'OPTION FAMILY V7: option tables={candidates}',flush=True)
    rows=[]
    for table in candidates:
        cols=[r[1] for r in con.execute(f'pragma table_info("{table}")')]
        lc={c.lower():c for c in cols}
        ts=next((lc[k] for k in ('timestamp','ts','datetime','bar_timestamp') if k in lc),None)
        ret=next((lc[k] for k in ('return','ret','pnl','forward_return') if k in lc),None)
        fam=next((lc[k] for k in ('family','strategy_family') if k in lc),None)
        if ts and ret:
            q=f'select "{ts}" as ts,"{ret}" as ret'+(f',"{fam}" as family' if fam else '')+f' from "{table}"'
            try: rows.extend(dict(r) for r in con.execute(q))
            except sqlite3.Error: pass
    con.close()

    print(f'OPTION FAMILY V7: discovered audit rows={len(rows)}',flush=True)
    # If the V6 artifact contains fold metrics, perform an artifact-level robustness audit.
    results=[]
    for i,f in enumerate(fams,1):
        name=family_name(f)
        folds=f.get('folds') or f.get('fold_metrics') or []
        vals=[]
        if isinstance(folds,dict): folds=list(folds.values())
        for z in folds:
            if isinstance(z,dict):
                for k in ('expectancy','median_expectancy','final_expectancy','base10','stress15'):
                    if isinstance(z.get(k),(int,float)) and math.isfinite(z[k]): vals.append(float(z[k])); break
        base=float(f.get('base10_median',0) or 0); stress=float(f.get('stress15_median',0) or 0)
        worst=float(f.get('worst',0) or 0); pf=f.get('worstPF')
        score=min(base,stress,worst)
        results.append({'family':name,'base10_median':base,'stress15_median':stress,'worst_fold':worst,'worst_pf':pf,'fold_values':vals,'robust_score':score})
        print(f'OPTION FAMILY V7: {i}/{len(fams)} {name} base={base:.6f} stress={stress:.6f} worst={worst:.6f} PF={pf}',flush=True)

    # Correlation/overlap cannot be safely inferred if event-level rows are not exposed by V6.
    # Mark it explicitly as pending rather than fabricating a result.
    out={'version':'v7','source':'option_family_v6.json','families':results,
         'deduplication':{'status':'pending_event_level_data','reason':'V6 artifact contains family-level fold metrics, not per-signal timestamps'},
         'drawdown':{'status':'pending_event_level_data'},
         'regime_concentration':{'status':'pending_event_level_data'},
         'next_gate':sum(1 for r in results if r['robust_score']>0 and (r['worst_pf'] or 0)>1.05),
         'elapsed_seconds':round(time.time()-t,2)}
    with open(a.out,'w',encoding='utf-8') as f: json.dump(out,f,indent=2)
    print(json.dumps({'families':len(results),'next_gate':out['next_gate'],'out':a.out,'elapsed_seconds':out['elapsed_seconds']}),flush=True)

if __name__=='__main__': main()
