from __future__ import annotations

import argparse
import json
import sqlite3
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def parse_name(name):
    p = name.split(":")
    side = p[0]
    strike = p[1] if len(p) > 1 else ""
    cond = tuple(sorted(x for x in (p[2].split("+") if len(p) > 2 else []) if x and x != "base"))
    return side, strike, cond


def family_sig(name):
    p = name.split(":")
    side = p[0]
    raw = p[2] if len(p) > 2 else (p[1] if len(p) == 2 else "")
    return side, tuple(sorted(x for x in raw.split("+") if x and x != "base"))


def enrich(rows):
    rows = sorted(rows, key=lambda r: r["timestamp"])
    if not rows:
        return []
    closes = [float(r.get("close") or 0) for r in rows]
    vols = [float(r.get("volume") or 0) for r in rows]
    e20 = e50 = closes[0]
    out = []
    for i, r in enumerate(rows):
        e20 = closes[i] * 2 / 21 + e20 * 19 / 21
        e50 = closes[i] * 2 / 51 + e50 * 49 / 51
        prior = rows[max(0, i - 20):i]
        avg_vol = sum(float(x.get("volume") or 0) for x in prior) / max(1, len(prior))
        spot = float(r.get("spot") or 0)
        spot0 = float(rows[max(0, i - 20)].get("spot") or 0) if i >= 20 else spot
        trend = spot / spot0 - 1 if spot0 else 0
        regime = "bull" if trend >= .01 else ("bear" if trend <= -.01 else "flat")
        out.append({**r, "ema20": e20, "ema50": e50, "rel_volume": vols[i] / avg_vol if avg_vol else 0, "regime": regime})
    return out


def match(r, cond):
    for c in cond:
        if c == "premium_trend" and not r["ema20"] > r["ema50"]: return False
        if c == "premium_weak" and not r["ema20"] < r["ema50"]: return False
        if c == "relvol_1_5" and r["rel_volume"] < 1.5: return False
        if c == "iv_high" and float(r.get("iv") or 0) <= 20: return False
        if c == "iv_low" and not 0 < float(r.get("iv") or 0) < 15: return False
        if c == "oi_present" and float(r.get("oi") or 0) <= 0: return False
    return True


def events_for(rows, family, cond, horizon, cost):
    e = enrich(rows); out = []
    for i, r in enumerate(e):
        if not match(r, cond): continue
        en, ex = i + 1, i + 1 + horizon
        if ex >= len(e): continue
        ep = float(e[en].get("open") or 0); xp = float(e[ex].get("close") or 0)
        if ep <= 0 or xp < 0: continue
        ret = max(xp / ep - 1 - cost / 10000, -1)
        out.append({"signal_timestamp": r["timestamp"], "entry_timestamp": e[en]["timestamp"], "exit_timestamp": e[ex]["timestamp"], "return": ret, "family": family, "strike_key": r["strike_key"], "regime": r["regime"]})
    return out


def simulate(events, initial, alloc, maxpos):
    by = defaultdict(list)
    for e in events: by[e["entry_timestamp"]].append(e)
    target = initial * alloc
    cash = initial; active = []; done = []; peak = initial; dd = 0.0
    for ts in sorted(by):
        for p in list(active):
            if p["exit_timestamp"] <= ts:
                cash += p["position_value"] + p["pnl"]
                done.append(p); active.remove(p)
        if len(active) < maxpos and cash >= target:
            for c in sorted(by[ts], key=lambda x: (x["family"], x["strike_key"])):
                if len(active) >= maxpos: break
                cash -= target
                active.append({**c, "position_value": target, "pnl": target * c["return"]})
        equity = cash + sum(p["position_value"] + p["pnl"] for p in active)
        peak = max(peak, equity); dd = min(dd, equity / peak - 1)
    for p in active:
        cash += p["position_value"] + p["pnl"]; done.append(p)
    pnls = [p["pnl"] for p in done]
    gross_win = sum(x for x in pnls if x > 0); gross_loss = -sum(x for x in pnls if x < 0)
    pf = gross_win / gross_loss if gross_loss else (float("inf") if gross_win else None)
    return {"trades": len(done), "return": sum(pnls) / initial if initial else 0, "profit_factor": pf, "drawdown": dd}


def pct(x): return f"{x:.2%}"


def main():
    p = argparse.ArgumentParser(description="V19 recent-period and walk-forward robustness audit")
    p.add_argument("--db", default="data/research/market_data.sqlite")
    p.add_argument("--input", default="data/research/option_family_v6.json")
    p.add_argument("--out", default="data/research/option_family_v19.json")
    p.add_argument("--horizon", type=int, default=6)
    p.add_argument("--cost-bps", type=float, default=5)
    p.add_argument("--slippage-bps", type=float, default=5)
    p.add_argument("--initial-capital", type=float, default=100000)
    p.add_argument("--allocation-pct", type=float, default=.02)
    p.add_argument("--max-positions", type=int, default=5)
    p.add_argument("--folds", type=int, default=5)
    a = p.parse_args(); start = time.time()
    src = json.loads(Path(a.input).read_text())
    fams = [x for x in src.get("results", []) if x.get("eligible_for_next_research_gate")]
    if not fams: raise SystemExit("V19 requires V6 eligible families.")
    db = sqlite3.connect(a.db); db.row_factory = sqlite3.Row
    cols = {r["name"] for r in db.execute("PRAGMA table_info(option_bars)")}
    required = {"timestamp","side","strike_key","open","close","volume","oi","iv","spot","contract_identity"}
    missing = required - cols
    if missing: raise SystemExit(f"Missing required columns: {sorted(missing)}")
    total, identities = db.execute("SELECT COUNT(*),COUNT(contract_identity) FROM option_bars").fetchone()
    if total != identities: raise SystemExit(f"Incomplete contract identity: {identities}/{total}")
    specs = set()
    for f in fams:
        side, cond = family_sig(f["family"])
        for n in f.get("matched_candidate_names", []):
            s, strike, cc = parse_name(n)
            if s == side and cc == cond: specs.add((s, strike))
    groups = {(s,k): [dict(r) for r in db.execute("SELECT timestamp,side,strike_key,open,close,volume,oi,iv,spot FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp", (s,k))] for s,k in sorted(specs)}
    db.close()
    events=[]; cost=a.cost_bps+a.slippage_bps
    for f in fams:
        family=f["family"]; side, cond=family_sig(family)
        for n in f.get("matched_candidate_names", []):
            s,k,cc=parse_name(n)
            if s==side and cc==cond: events.extend(events_for(groups.get((s,k),[]),family,cond,a.horizon,cost))
    events.sort(key=lambda x:x["entry_timestamp"])
    if not events: raise SystemExit("V19 generated zero events.")
    ts=sorted({e["entry_timestamp"] for e in events}); start_ts=ts[0]; end_ts=ts[-1]

    windows=[]
    for days in (90,180,365,540):
        lo=end_ts-days*86400
        es=[e for e in events if e["entry_timestamp"]>=lo]
        r=simulate(es,a.initial_capital,a.allocation_pct,a.max_positions)
        windows.append({"window_days":days,"events":len(es),**r})
        print(f"OPTION FAMILY V19: recent={days}d events={len(es)} trades={r['trades']} return={pct(r['return'])} PF={r['profit_factor']} DD={pct(r['drawdown'])}",flush=True)

    nfold=max(3,a.folds); fold_results=[]
    # Each fold is a chronological validation slice; no event from a later slice is used in an earlier slice.
    for i in range(nfold):
        lo_idx=(i*len(ts))//nfold; hi_idx=((i+1)*len(ts))//nfold
        if i==nfold-1: hi_idx=len(ts)
        if hi_idx<=lo_idx: continue
        lo_ts=ts[lo_idx]; hi_ts=ts[hi_idx-1]
        es=[e for e in events if lo_ts<=e["entry_timestamp"]<=hi_ts]
        r=simulate(es,a.initial_capital,a.allocation_pct,a.max_positions)
        fold_results.append({"fold":i+1,"start":lo_ts,"end":hi_ts,"trades":r["trades"],**r})
        print(f"OPTION FAMILY V19: walk_forward_fold={i+1} trades={r['trades']} return={pct(r['return'])} PF={r['profit_factor']} DD={pct(r['drawdown'])}",flush=True)

    family_pnl=defaultdict(float)
    for e in events: family_pnl[e["family"]]+=e["return"]
    ranked=sorted(family_pnl.items(),key=lambda x:x[1],reverse=True)
    top_share=(ranked[0][1]/sum(x for _,x in ranked)) if ranked and sum(x for _,x in ranked)>0 else 0
    recent6=windows[1]; recent12=windows[2]
    positive_recent=sum(x["return"]>0 and (x["profit_factor"] or 0)>=1.05 for x in windows)/len(windows)
    positive_folds=sum(x["return"]>0 and (x["profit_factor"] or 0)>=1.05 for x in fold_results)/len(fold_results) if fold_results else 0
    reasons=[]
    if recent6["trades"]<500 or (recent6["profit_factor"] or 0)<1.05: reasons.append("recent_6m_failure")
    if recent12["trades"]<1000 or (recent12["profit_factor"] or 0)<1.05: reasons.append("recent_12m_failure")
    if positive_folds<.80: reasons.append("walk_forward_failure")
    if top_share>.70: reasons.append("family_concentration_failure")

    result={"version":"v19","purpose":"recent-period, chronological walk-forward and concentration robustness","events":len(events),"data_quality":{"option_bar_rows":total,"contract_identity_complete":total==identities},"data_range":{"start":datetime.fromtimestamp(start_ts,tz=timezone.utc).isoformat(),"end":datetime.fromtimestamp(end_ts,tz=timezone.utc).isoformat()},"recent_windows":windows,"walk_forward":fold_results,"family_pnl_share":{"top_family":ranked[0][0] if ranked else None,"top_family_share":top_share,"ranking":ranked},"positive_recent_rate":positive_recent,"positive_walk_forward_rate":positive_folds,"gate_reasons":reasons,"next_gate":not reasons,"promotion_status":"RESEARCH_ONLY_NO_LIVE_TRADING","elapsed_seconds":round(time.time()-start,2)}
    Path(a.out).write_text(json.dumps(result,indent=2)); print(json.dumps({"events":len(events),"recent_6m_pf":recent6["profit_factor"],"recent_12m_pf":recent12["profit_factor"],"positive_walk_forward_rate":positive_folds,"top_family_share":top_share,"gate_reasons":reasons,"next_gate":not reasons,"out":a.out,"elapsed_seconds":result["elapsed_seconds"]},indent=2),flush=True)

if __name__=="__main__": main()
