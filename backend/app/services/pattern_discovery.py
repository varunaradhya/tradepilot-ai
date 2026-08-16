from __future__ import annotations
from dataclasses import dataclass, asdict
from math import isfinite
from statistics import median

@dataclass(frozen=True)
class PatternRule:
    name: str
    conditions: tuple[str, ...]
    occurrences: int
    win_rate: float
    expectancy: float
    median_forward_return: float
    positive_forward_return: float
    max_forward_return: float
    min_forward_return: float
    train_score: float
    test_score: float
    robust: bool

    def to_dict(self): return asdict(self)

def _ema(values, period):
    if not values:return []
    k=2/(period+1); out=[float(values[0])];
    for x in values[1:]: out.append(float(x)*k+out[-1]*(1-k))
    return out

def _rsi(closes, period=14):
    if len(closes)<2:return [50.0]*len(closes)
    gains=[];losses=[]
    for a,b in zip(closes[:-1],closes[1:]):
        d=b-a;gains.append(max(d,0));losses.append(max(-d,0))
    ag=sum(gains[:period])/max(period,1); al=sum(losses[:period])/max(period,1); out=[50.0]*(period+1)
    for i in range(period,len(gains)):
        ag=(ag*(period-1)+gains[i])/period; al=(al*(period-1)+losses[i])/period
        out.append(100.0 if al==0 else 100-100/(1+ag/al))
    return out[:len(closes)] + [50.0]*max(0,len(closes)-len(out))

def enrich_bars(rows):
    rows=sorted(rows,key=lambda r:r['timestamp']); closes=[float(r['close']) for r in rows]
    ema20=_ema(closes,20); ema50=_ema(closes,50); rsi=_rsi(closes,14)
    out=[]; prev_close=None
    for i,r in enumerate(rows):
        c=closes[i]; rng=max(float(r['high'])-float(r['low']),1e-9); body=abs(c-float(r['open']))
        vol=float(r.get('volume') or 0); start=max(0,i-20); avg=sum(float(x.get('volume') or 0) for x in rows[start:i])/max(i-start,1)
        out.append({**r,'ema20':ema20[i],'ema50':ema50[i],'rsi':rsi[i],'rel_volume':vol/avg if avg else 0.0,'body_ratio':body/rng,'ret_1':(c/prev_close-1) if prev_close else 0.0})
        prev_close=c
    return out

def forward_returns(rows, horizon=6):
    closes=[float(r['close']) for r in rows]; out=[None]*len(rows)
    for i in range(len(rows)-horizon):
        out[i]=closes[i+horizon]/closes[i]-1
    return out

def _stats(vals):
    vals=[v for v in vals if v is not None and isfinite(v)]
    if not vals:return None
    wins=[v for v in vals if v>0]
    return len(vals),len(wins)/len(vals),sum(vals)/len(vals),median(vals),max(vals),min(vals)

def discover_patterns(rows, horizon=6, min_occurrences=50, train_ratio=.7):
    """Mine interpretable, pre-declared threshold combinations; no target-driven thresholds."""
    rows=enrich_bars(rows); fwd=forward_returns(rows,horizon)
    split=max(1,int(len(rows)*train_ratio)); train=rows[:split]; test=rows[split:]
    train_fwd=fwd[:split]; test_fwd=fwd[split:]
    conditions={
        'trend_up':lambda r:r['ema20']>r['ema50'],
        'trend_down':lambda r:r['ema20']<r['ema50'],
        'rsi_55_70':lambda r:55<=r['rsi']<=70,
        'rsi_30_45':lambda r:30<=r['rsi']<=45,
        'relvol_1_5':lambda r:r['rel_volume']>=1.5,
        'relvol_2':lambda r:r['rel_volume']>=2.0,
        'body_60':lambda r:r['body_ratio']>=.60,
        'positive_1bar':lambda r:r['ret_1']>0,
        'negative_1bar':lambda r:r['ret_1']<0,
    }
    combos=[]
    names=list(conditions)
    for a in names:
        for b in names:
            if b<=a: continue
            for c in names:
                if c<=b: continue
                combos.append((a,b,c))
    results=[]
    for combo in combos:
        mask_train=[all(conditions[x](r) for x in combo) for r in train]
        mask_test=[all(conditions[x](r) for x in combo) for r in test]
        tv=[v for m,v in zip(mask_train,train_fwd) if m and v is not None]
        qv=[v for m,v in zip(mask_test,test_fwd) if m and v is not None]
        if len(tv)<min_occurrences or len(qv)<max(20,min_occurrences//2): continue
        ts=_stats(tv); qs=_stats(qv)
        robust=ts[2]>0 and qs[2]>0 and qs[1]>=.52
        train_score=ts[2]*100*min(1,ts[0]/500)
        test_score=qs[2]*100*min(1,qs[0]/200)
        results.append(PatternRule('+'.join(combo),combo,ts[0],ts[1],ts[2],ts[3],ts[1],ts[4],ts[5],train_score,test_score,robust))
    return sorted(results,key=lambda x:(x.robust,x.test_score,x.test_score-x.train_score),reverse=True)

def discover_equity_patterns(rows, horizon=6, min_occurrences=50):
    return discover_patterns(rows,horizon,min_occurrences)
