from __future__ import annotations
import argparse,json,math,statistics,time
from pathlib import Path

def pct(values, q):
    if not values: return 0.0
    x=sorted(values); pos=(len(x)-1)*q; lo=math.floor(pos); hi=math.ceil(pos)
    return x[lo] if lo==hi else x[lo]+(x[hi]-x[lo])*(pos-lo)

def trimmed_mean(values, trim=0.10):
    if not values: return 0.0
    x=sorted(values); k=int(len(x)*trim)
    y=x[k:len(x)-k] if len(x)>2*k else x
    return statistics.mean(y)

def family_key(name):
    parts=name.split(':')
    if len(parts)<3: return name
    side,strike=parts[:2]; conditions=parts[2:]
    # The core family deliberately ignores redundant confirmation suffixes.
    core=[]
    for c in conditions:
        if c in {'oi_present','iv_low','iv_high'}: continue
        core.append(c)
    return f'{side}:{strike}:{"+".join(sorted(core))}'

def main():
    p=argparse.ArgumentParser(description='Audit V3 option candidates for family redundancy, outlier dependence and stability. Research-only; no execution promotion.')
    p.add_argument('--input',default='data/research/option_oos_v3.json')
    p.add_argument('--out',default='data/research/option_family_audit_v4.json')
    p.add_argument('--min-trades',type=int,default=25)
    p.add_argument('--min-mc-positive',type=float,default=.55)
    a=p.parse_args(); started=time.time()
    src=json.loads(Path(a.input).read_text(encoding='utf-8'))
    results=src.get('results',[])
    families={}
    for r in results:
        k=family_key(r['name']); families.setdefault(k,[]).append(r)
    print(f'OPTION FAMILY V4: candidates={len(results)} families={len(families)}',flush=True)
    family_rows=[]
    for i,(key,rows) in enumerate(sorted(families.items()),1):
        final_returns=[]
        for r in rows:
            # V3 stores final aggregate return but not individual trades. Use expectancy as the robust per-trade measure.
            if r.get('final_trades',0)>=a.min_trades:
                final_returns.append(float(r.get('final_expectancy',0)))
        best=max(rows,key=lambda r: float(r.get('final_expectancy',-1e99)))
        expect=[float(r.get('final_expectancy',0)) for r in rows]
        positive=sum(x>0 for x in expect)/len(expect) if expect else 0
        trimmed=trimmed_mean(expect)
        row={'family':key,'variants':len(rows),'positive_variant_rate':positive,'median_expectancy':statistics.median(expect) if expect else 0.0,'trimmed_mean_expectancy':trimmed,'best_expectancy':float(best.get('final_expectancy',0)),'best_name':best['name'],'best_profit_factor':best.get('final_profit_factor'),'best_final_trades':best.get('final_trades',0),'best_mc_positive_probability':best.get('monte_carlo',{}).get('probability_positive',0),'eligible_for_next_gate':bool(positive>=.50 and trimmed>0 and best.get('final_trades',0)>=a.min_trades and best.get('monte_carlo',{}).get('probability_positive',0)>=a.min_mc_positive)}
        family_rows.append(row)
        print(f'OPTION FAMILY V4: {i}/{len(families)} {key} variants={len(rows)} positive={positive:.2f} trimmed_expectancy={trimmed:.6f} next_gate={row["eligible_for_next_gate"]}',flush=True)
    # Outlier warning: extremely high best expectancy compared with the family median is a research red flag.
    for row in family_rows:
        row['outlier_dependence_flag']=bool(row['median_expectancy']>0 and row['best_expectancy']>max(5*row['median_expectancy'],0.01))
    family_rows.sort(key=lambda x:(x['eligible_for_next_gate'],x['trimmed_mean_expectancy']),reverse=True)
    report={'methodology':{'family_definition':'same side/strike/core conditions; OI/IV confirmation suffixes treated as variants','outlier_rule':'best expectancy > 5x family median','min_trades':a.min_trades,'min_mc_positive_probability':a.min_mc_positive},'input_candidates':len(results),'families':len(family_rows),'next_gate_candidates':[x for x in family_rows if x['eligible_for_next_gate']],'all_families':family_rows,'promotion_status':'RESEARCH_ONLY_NO_PAPER_TRADING','critical_limit':'V3/V4 use rolling option series. Exact historical contract, expiry, spread, fill and lot execution remain unvalidated.'}
    report['elapsed_seconds']=round(time.time()-started,2)
    Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'candidates':len(results),'families':len(family_rows),'next_gate':len(report['next_gate_candidates']),'elapsed_seconds':report['elapsed_seconds'],'out':a.out},indent=2),flush=True)
if __name__=='__main__': main()
