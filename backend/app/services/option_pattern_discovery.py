from __future__ import annotations
from app.services.pattern_discovery import PatternRule, _discover, _ema

def discover_option_patterns(rows, horizon=6, min_occurrences=50):
    rows=sorted(rows,key=lambda r:(r.get('side',''),r.get('strike_key',''),r['timestamp']))
    results=[];groups={}
    for r in rows: groups.setdefault((r.get('side',''),r.get('strike_key','')),[]).append(r)
    for key,g in groups.items():
        if len(g)<min_occurrences*2: continue
        closes=[float(r['close']) for r in g]; ema20=_ema(closes,20); ema50=_ema(closes,50)
        enriched=[]
        for i,r in enumerate(g):
            vol=float(r.get('volume') or 0); start=max(0,i-20); avg=sum(float(x.get('volume') or 0) for x in g[start:i])/max(i-start,1)
            enriched.append({**r,'ema20':ema20[i],'ema50':ema50[i],'rel_volume':vol/avg if avg else 0,'iv':float(r.get('iv') or 0),'oi':float(r.get('oi') or 0)})
        conditions={'premium_trend':lambda r:r['ema20']>r['ema50'],'premium_weak':lambda r:r['ema20']<r['ema50'],'relvol_1_5':lambda r:r['rel_volume']>=1.5,'iv_high':lambda r:r['iv']>20,'iv_low':lambda r:0<r['iv']<15,'oi_present':lambda r:r['oi']>0}
        found=_discover(enriched,conditions,horizon,min_occurrences)
        for x in found:
            results.append(PatternRule(f'{key[0]}:{key[1]}:{x.name}',x.conditions,x.occurrences,x.win_rate,x.expectancy,x.median_forward_return,x.positive_forward_return,x.max_forward_return,x.min_forward_return,x.train_score,x.test_score,x.robust))
    return sorted(results,key=lambda x:(x.robust,x.test_score),reverse=True)
