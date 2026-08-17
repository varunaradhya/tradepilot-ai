from __future__ import annotations
import argparse, json, sqlite3, statistics, time
from collections import defaultdict
from pathlib import Path


def parse_name(n):
    p=n.split(":")
    side=p[0]
    strike=p[1] if len(p)>1 else ""
    cond=tuple(sorted(x for x in (p[2].split("+") if len(p)>2 else []) if x and x != "base"))
    return side, strike, cond


def family_sig(n):
    p=n.split(":")
    return p[0], tuple(sorted(x for x in (p[2].split("+") if len(p)>2 else []) if x and x != "base"))


def enrich(rows):
    rows=sorted(rows,key=lambda r:r["timestamp"])
    if not rows:return []
    c=[float(r["close"]) for r in rows]
    e20=[]; e50=[]; a=b=c[0]
    for x in c:
        a=x*(2/21)+a*(19/21); b=x*(2/51)+b*(49/51)
        e20.append(a); e50.append(b)
    out=[]
    for i,r in enumerate(rows):
        prior=rows[max(0,i-20):i]
        av=sum(float(x.get("volume") or 0) for x in prior)/max(1,len(prior))
        out.append({**r,"ema20":e20[i],"ema50":e50[i],"rel_volume":float(r.get("volume") or 0)/av if av else 0})
    return out


def signal(r,cond):
    for c in cond:
        if c=="premium_trend" and not r["ema20"]>r["ema50"]: return False
        if c=="premium_weak" and not r["ema20"]<r["ema50"]: return False
        if c=="relvol_1_5" and not r["rel_volume"]>=1.5: return False
        if c=="iv_high" and not float(r.get("iv") or 0)>20: return False
        if c=="iv_low" and not 0<float(r.get("iv") or 0)<15: return False
        if c=="oi_present" and not float(r.get("oi") or 0)>0: return False
    return True


def build(rows,family,cond,horizon,cost,delay=1):
    e=enrich(rows); out=[]
    for i in range(len(e)-horizon-delay):
        if not signal(e[i],cond): continue
        j=i+delay; x=i+horizon
        entry=float(e[j]["open"]); exit_=float(e[x]["close"])
        if entry<=0 or exit_<0: continue
        ret=max(exit_/entry-1-cost,-1)
        out.append({"timestamp":e[i]["timestamp"],"exit_timestamp":e[x]["timestamp"],"return":ret,"family":family,"strike_key":e[i]["strike_key"]})
    return out


def stats(events,initial=100000,alloc=.02,maxpos=5):
    by=defaultdict(list)
    for e in events: by[e["timestamp"]].append(e)
    fixed=initial*alloc; cash=initial; active=[]; done=[]; peak=initial; dd=0
    for ts in sorted(by):
        keep=[]
        for p in active:
            if p["exit_timestamp"]<=ts:
                cash+=p["value"]+p["pnl"]; done.append(p)
            else: keep.append(p)
        active=keep
        if len(active)>=maxpos or cash<fixed: continue
        c=sorted(by[ts],key=lambda x:(x["family"],x["strike_key"]))[0]
        cash-=fixed; active.append({**c,"value":fixed,"pnl":fixed*c["return"]})
        eq=cash+sum(p["value"]+p["pnl"] for p in active); peak=max(peak,eq); dd=min(dd,eq/peak-1)
    for p in active: cash+=p["value"]+p["pnl"]; done.append(p)
    pnls=[p["pnl"] for p in done]; wins=[x for x in pnls if x>0]; losses=[-x for x in pnls if x<0]
    pf=sum(wins)/sum(losses) if losses else (float("inf") if wins else None)
    return {"trades":len(done),"expectancy":statistics.mean([p["return"] for p in done]) if done else 0,"profit_factor":pf,"return_pct":sum(pnls)/initial if initial else 0,"max_drawdown_pct":dd}


def main():
    p=argparse.ArgumentParser(description="V16 next-bar-open family stability and strict holdout audit")
    p.add_argument("--db",default="data/research/market_data.sqlite"); p.add_argument("--input",default="data/research/option_family_v6.json"); p.add_argument("--out",default="data/research/option_family_v16.json")
    p.add_argument("--horizon",type=int,default=6); p.add_argument("--cost-bps",type=float,default=5); p.add_argument("--slippage-bps",type=float,default=5); p.add_argument("--initial-capital",type=float,default=100000); p.add_argument("--allocation-pct",type=float,default=.02); p.add_argument("--max-positions",type=int,default=5); p.add_argument("--folds",type=int,default=4)
    a=p.parse_args(); start=time.time(); src=json.loads(Path(a.input).read_text())
    fam=[x for x in src.get("results",[]) if x.get("eligible_for_next_research_gate")]
    if not fam: raise SystemExit("V16 requires V6 eligible families")
    db=sqlite3.connect(a.db); db.row_factory=sqlite3.Row
    cols=[r["name"] for r in db.execute("PRAGMA table_info(option_bars)")]
    if "contract_identity" not in cols: raise SystemExit("V16 requires contract_identity")
    total,ident=db.execute("SELECT COUNT(*),COUNT(contract_identity) FROM option_bars").fetchone()
    if total!=ident: raise SystemExit(f"Incomplete contract identity: {ident}/{total}")
    specs=set()
    for f in fam:
        side,cond=family_sig(f["family"])
        for n in f.get("matched_candidate_names",[]):
            s,k,c=parse_name(n)
            if s==side and c==cond: specs.add((s,k))
    groups={k:[dict(r) for r in db.execute("SELECT timestamp,side,strike_key,open,close,volume,oi,iv FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp",k)] for k in specs}
    db.close(); cost=(a.cost_bps+a.slippage_bps)/10000
    events=[]
    for f in fam:
        side,cond=family_sig(f["family"])
        for n in f.get("matched_candidate_names",[]):
            s,k,c=parse_name(n)
            if s==side and c==cond: events.extend(build(groups.get((s,k),[]),f["family"],cond,a.horizon,cost,1))
    events.sort(key=lambda x:(x["timestamp"],x["family"],x["strike_key"]))
    ts=sorted({e["timestamp"] for e in events}); cutoff=ts[max(0,int(len(ts)*.8)-1)] if ts else 0
    hold=[e for e in events if e["timestamp"]>cutoff]; pre=[e for e in events if e["timestamp"]<=cutoff]
    overall=stats(events,a.initial_capital,a.allocation_pct,a.max_positions); strict=stats(hold,a.initial_capital,a.allocation_pct,a.max_positions)
    folds=[]
    for i in range(a.folds):
        lo=ts[(i*len(ts))//a.folds]; hi=ts[((i+1)*len(ts))//a.folds-1] if i==a.folds-1 else ts[((i+1)*len(ts))//a.folds]
        fe=[e for e in events if lo<=e["timestamp"]<=hi]
        r=stats(fe,a.initial_capital,a.allocation_pct,a.max_positions); folds.append({"fold":i+1,"start":lo,"end":hi,**r})
    families=[]
    for name in [f["family"] for f in fam]:
        ev=[e for e in events if e["family"]==name]; r=stats(ev,a.initial_capital,a.allocation_pct,min(a.max_positions,3)); families.append({"family":name,**r,"event_share":len(ev)/len(events) if events else 0})
    positive=sum(1 for f in folds if f["profit_factor"] is not None and f["profit_factor"]>1.05)
    reasons=[]
    if strict["profit_factor"] is None or strict["profit_factor"]<1.10 or strict["return_pct"]<=0: reasons.append("strict_holdout_failure")
    if positive<a.folds: reasons.append("fold_instability")
    if any(f["event_share"]>0.80 for f in families): reasons.append("family_concentration")
    result={"version":"v16","purpose":"next-bar-open robustness, strict holdout and family stability","execution":"signal at completed bar close; entry at next bar open; exit at horizon-bar close","cost_bps_round_trip":a.cost_bps+a.slippage_bps,"events":len(events),"overall":overall,"strict_holdout":strict,"folds":folds,"family_results":families,"positive_fold_rate":positive/a.folds if a.folds else 0,"gate_reasons":reasons,"next_gate":not reasons,"promotion_status":"RESEARCH_ONLY_NO_PAPER_TRADING","elapsed_seconds":round(time.time()-start,2)}
    Path(a.out).write_text(json.dumps(result,indent=2)); print(json.dumps({"events":len(events),"strict_holdout_pf":strict["profit_factor"],"strict_holdout_return":strict["return_pct"],"positive_fold_rate":result["positive_fold_rate"],"gate_reasons":reasons,"next_gate":result["next_gate"],"out":a.out,"elapsed_seconds":result["elapsed_seconds"]},indent=2))

if __name__=="__main__": main()
