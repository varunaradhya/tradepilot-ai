from __future__ import annotations

import argparse, json, math, time


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
    a=parse_args(); started=time.time()
    with open(a.input,encoding='utf-8') as f:
        src=json.load(f)
    if not isinstance(src,dict):
        raise SystemExit('V7 input must be a JSON object')

    raw=src.get('results',[])
    if not isinstance(raw,list):
        raise SystemExit('V7 expected input.results to be a list')
    fams=[r for r in raw if r.get('eligible_for_next_research_gate')]
    names=[family_name(r) for r in fams]
    print(f'OPTION FAMILY V7: V6 eligible families={len(fams)} {names}',flush=True)

    results=[]
    for i,row in enumerate(fams,1):
        name=family_name(row)
        sensitivity=row.get('cost_sensitivity') or {}
        base=sensitivity.get('10') or {}
        stress=sensitivity.get('15') or {}
        stress20=sensitivity.get('20') or {}
        base_folds=base.get('folds') or []
        vals=[float(x.get('expectancy')) for x in base_folds if isinstance(x,dict) and isinstance(x.get('expectancy'),(int,float)) and math.isfinite(x.get('expectancy'))]
        worst=min(vals) if vals else 0.0
        pfs=[float(x.get('profit_factor')) for x in base_folds if isinstance(x,dict) and isinstance(x.get('profit_factor'),(int,float)) and math.isfinite(x.get('profit_factor'))]
        worst_pf=min(pfs) if pfs else None
        base_median=float(base.get('median_expectancy') or 0.0)
        stress_median=float(stress.get('median_expectancy') or 0.0)
        stress20_median=float(stress20.get('median_expectancy') or 0.0)
        robust_score=min(base_median,stress_median,worst)
        result={
            'family':name,
            'v6_eligible':True,
            'base10_median':base_median,
            'stress15_median':stress_median,
            'stress20_median':stress20_median,
            'worst_fold_expectancy':worst,
            'worst_fold_profit_factor':worst_pf,
            'fold_values':vals,
            'robust_score':robust_score,
            'v6_rejection_reasons':row.get('rejection_reasons',[]),
        }
        results.append(result)
        print(f'OPTION FAMILY V7: {i}/{len(fams)} {name} base10={base_median:.6f} stress15={stress_median:.6f} stress20={stress20_median:.6f} worst={worst:.6f} worstPF={worst_pf} score={robust_score:.6f}',flush=True)

    out={
        'version':'v7',
        'source':'option_family_v6.json',
        'families':len(results),
        'results':results,
        'deduplication':{'status':'pending_event_level_data','reason':'V6 artifact contains family-level fold metrics, not per-signal timestamps'},
        'drawdown':{'status':'pending_event_level_data'},
        'regime_concentration':{'status':'pending_event_level_data'},
        'next_gate':sum(1 for r in results if r['robust_score']>0 and (r['worst_fold_profit_factor'] or 0)>1.05),
        'promotion_status':'RESEARCH_ONLY_NO_PAPER_TRADING',
        'elapsed_seconds':round(time.time()-started,2),
    }
    with open(a.out,'w',encoding='utf-8') as f:
        json.dump(out,f,indent=2)
    print(json.dumps({'families':len(results),'next_gate':out['next_gate'],'out':a.out,'elapsed_seconds':out['elapsed_seconds']}),flush=True)

if __name__=='__main__':
    main()
