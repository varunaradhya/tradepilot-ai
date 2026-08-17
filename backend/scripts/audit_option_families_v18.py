from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import time
from collections import defaultdict
from pathlib import Path


def parse_name(name):
    p = name.split(":")
    return p[0], p[1] if len(p) > 1 else "", tuple(sorted(x for x in (p[2].split("+") if len(p) > 2 else []) if x and x != "base"))


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
    ema20, ema50, out = [], [], []
    a = b = closes[0]
    for x in closes:
        a = x * 2 / 21 + a * 19 / 21
        b = x * 2 / 51 + b * 49 / 51
        ema20.append(a); ema50.append(b)
    for i, r in enumerate(rows):
        prior = rows[max(0, i - 20):i]
        avg = sum(float(x.get("volume") or 0) for x in prior) / max(1, len(prior))
        spot = float(r.get("spot") or 0)
        spot0 = float(rows[max(0, i - 20)].get("spot") or 0) if i >= 20 else spot
        trend = (spot / spot0 - 1) if spot0 else 0
        regime = "bull" if trend >= 0.01 else ("bear" if trend <= -0.01 else "flat")
        out.append({**r, "ema20": ema20[i], "ema50": ema50[i], "rel_volume": vols[i] / avg if avg else 0, "regime": regime})
    return out


def condition_match(r, cond):
    for c in cond:
        if c == "premium_trend" and not r["ema20"] > r["ema50"]: return False
        if c == "premium_weak" and not r["ema20"] < r["ema50"]: return False
        if c == "relvol_1_5" and r["rel_volume"] < 1.5: return False
        if c == "iv_high" and float(r.get("iv") or 0) <= 20: return False
        if c == "iv_low" and not 0 < float(r.get("iv") or 0) < 15: return False
        if c == "oi_present" and float(r.get("oi") or 0) <= 0: return False
    return True


def build_events(rows, family, cond, horizon, cost_bps):
    e = enrich(rows); out = []
    for i, r in enumerate(e):
        if not condition_match(r, cond): continue
        entry_i, exit_i = i + 1, i + 1 + horizon
        if exit_i >= len(e): continue
        ep = float(e[entry_i].get("open") or 0); xp = float(e[exit_i].get("close") or 0)
        if ep <= 0 or xp < 0: continue
        ret = max(xp / ep - 1 - cost_bps / 10000, -1)
        out.append({"signal_timestamp": r["timestamp"], "entry_timestamp": e[entry_i]["timestamp"], "exit_timestamp": e[exit_i]["timestamp"], "return": ret, "family": family, "strike_key": r["strike_key"], "entry_volume": float(e[entry_i].get("volume") or 0), "entry_oi": float(e[entry_i].get("oi") or 0), "entry_price": ep, "regime": r["regime"]})
    return out


def simulate(events, initial, alloc, maxpos, daily_loss_limit=0.03, family_cap=1.0, cooldown_losses=0):
    by = defaultdict(list)
    for e in events: by[e["entry_timestamp"]].append(e)
    target = initial * alloc; cash = initial; active = []; done = []; peak = initial; dd = 0.0
    day_pnl = 0.0; current_day = None; loss_streak = 0; cooldown = 0; skipped = 0
    family_active = defaultdict(int); maxexp = 0.0
    for ts in sorted(by):
        day = ts // 86400
        if day != current_day:
            current_day, day_pnl = day, 0.0
            if cooldown: cooldown -= 1
        for p in list(active):
            if p["exit_timestamp"] <= ts:
                cash += p["position_value"] + p["pnl"]; day_pnl += p["pnl"]; done.append(p); family_active[p["family"]] -= 1; active.remove(p)
                if p["pnl"] < 0: loss_streak += 1
                else: loss_streak = 0
                if cooldown_losses and loss_streak >= cooldown_losses: cooldown = 1; loss_streak = 0
        used = sum(p["position_value"] for p in active)
        candidates = sorted(by[ts], key=lambda x: (x["family"], x["strike_key"]))
        if cooldown or day_pnl <= -initial * daily_loss_limit or len(active) >= maxpos or not candidates:
            skipped += 1
        else:
            c = next((x for x in candidates if family_active[x["family"]] < max(1, int(maxpos * family_cap))), None)
            if c is None or cash < target or used + target > initial:
                skipped += 1
            else:
                cash -= target
                active.append({**c, "position_value": target, "pnl": target * c["return"]})
                family_active[c["family"]] += 1
                maxexp = max(maxexp, (used + target) / initial)
        equity = cash + sum(p["position_value"] + p["pnl"] for p in active)
        peak = max(peak, equity); dd = min(dd, equity / peak - 1)
    for p in sorted(active, key=lambda x: x["exit_timestamp"]):
        cash += p["position_value"] + p["pnl"]; done.append(p)
    pnls = [p["pnl"] for p in done]; wins = sum(x for x in pnls if x > 0); losses = -sum(x for x in pnls if x < 0)
    return {"trades": len(done), "return_pct": sum(pnls) / initial if initial else 0, "profit_factor": wins / losses if losses else (float("inf") if wins else None), "max_drawdown_pct": dd, "max_exposure_pct": maxexp, "skipped": skipped, "win_rate": sum(x > 0 for x in pnls) / len(pnls) if pnls else 0}


def main():
    p = argparse.ArgumentParser(description="V18 portfolio, regime and risk robustness audit")
    p.add_argument("--db", default="data/research/market_data.sqlite"); p.add_argument("--input", default="data/research/option_family_v6.json"); p.add_argument("--out", default="data/research/option_family_v18.json")
    p.add_argument("--horizon", type=int, default=6); p.add_argument("--cost-bps", type=float, default=5); p.add_argument("--slippage-bps", type=float, default=5)
    p.add_argument("--initial-capital", type=float, default=100000); p.add_argument("--allocation-pct", type=float, default=.02); p.add_argument("--max-positions", type=int, default=5)
    a = p.parse_args(); start = time.time()
    src = json.loads(Path(a.input).read_text())
    fam = [r for r in src.get("results", []) if r.get("eligible_for_next_research_gate")]
    if not fam: raise SystemExit("V18 requires V6 eligible families.")
    db = sqlite3.connect(a.db); db.row_factory = sqlite3.Row
    cols = {r["name"] for r in db.execute("PRAGMA table_info(option_bars)")}; required = {"timestamp","side","strike_key","open","close","volume","oi","iv","spot","contract_identity"}
    if required - cols: raise SystemExit(f"Missing required columns: {sorted(required-cols)}")
    total, identity = db.execute("SELECT COUNT(*),COUNT(contract_identity) FROM option_bars").fetchone()
    if total != identity: raise SystemExit(f"Incomplete contract identity: {identity}/{total}")
    specs = sorted({(parse_name(n)[0], parse_name(n)[1]) for f in fam for n in f.get("matched_candidate_names", [])}); groups = {}
    for side, strike in specs:
        groups[(side,strike)] = [dict(r) for r in db.execute("SELECT timestamp,side,strike_key,open,close,volume,oi,iv,spot FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp", (side,strike))]
    db.close(); events=[]; cost=a.cost_bps+a.slippage_bps
    for f in fam:
        family=f["family"]; side,cond=family_sig(family)
        for n in f.get("matched_candidate_names", []):
            s,strike,cc=parse_name(n)
            if s==side and cc==cond: events.extend(build_events(groups.get((s,strike),[]),family,cond,a.horizon,cost))
    events.sort(key=lambda x:(x["entry_timestamp"],x["family"],x["strike_key"]))
    if not events: raise SystemExit("V18 generated zero events.")

    scenarios=[]
    for name, kwargs in [("baseline",{}),("daily_loss_2pct",{"daily_loss_limit":.02}),("daily_loss_1pct",{"daily_loss_limit":.01}),("family_cap_40pct",{"family_cap":.4}),("cooldown_after_3_losses",{"cooldown_losses":3})]:
        r=simulate(events,a.initial_capital,a.allocation_pct,a.max_positions,**kwargs); scenarios.append({"name":name,**r})
        print(f"OPTION FAMILY V18: {name} trades={r['trades']} return={r['return_pct']:.2%} PF={r['profit_factor']} DD={r['max_drawdown_pct']:.2%} exposure={r['max_exposure_pct']:.2%}",flush=True)

    regime=[]
    for reg in ("bull","flat","bear"):
        es=[e for e in events if e["regime"]==reg]; r=simulate(es,a.initial_capital,a.allocation_pct,a.max_positions); regime.append({"regime":reg,"events":len(es),**r})
        print(f"OPTION FAMILY V18: regime={reg} events={len(es)} trades={r['trades']} return={r['return_pct']:.2%} PF={r['profit_factor']} DD={r['max_drawdown_pct']:.2%}",flush=True)

    years=[]
    for year in sorted({__import__('datetime').datetime.fromtimestamp(e["entry_timestamp"]).year for e in events}):
        es=[e for e in events if __import__('datetime').datetime.fromtimestamp(e["entry_timestamp"]).year==year]; r=simulate(es,a.initial_capital,a.allocation_pct,a.max_positions); years.append({"year":year,"events":len(es),**r})
        print(f"OPTION FAMILY V18: year={year} events={len(es)} trades={r['trades']} return={r['return_pct']:.2%} PF={r['profit_factor']} DD={r['max_drawdown_pct']:.2%}",flush=True)

    risk=[x for x in scenarios if x["name"]!="baseline"]
    populated_regimes=[x for x in regime if x["trades"]>=100]
    positive_regime_rate=sum(x["return_pct"]>0 for x in populated_regimes)/len(populated_regimes) if populated_regimes else 0
    populated_years=[x for x in years if x["trades"]>=100]
    positive_year_rate=sum(x["return_pct"]>0 for x in populated_years)/len(populated_years) if populated_years else 0
    reasons=[]
    if len(populated_regimes)<2 or positive_regime_rate<.67: reasons.append("regime_robustness_failure")
    if len(populated_years)<3 or positive_year_rate<.60: reasons.append("calendar_year_robustness_failure")
    if any(x["profit_factor"] is None or x["profit_factor"]<1.05 or x["return_pct"]<=0 for x in risk): reasons.append("risk_control_failure")

    result={"version":"v18","purpose":"portfolio risk, market-regime and calendar-year robustness audit","events":len(events),"data_quality":{"option_bar_rows":total,"contract_identity_complete":total==identity,"bid_ask_available":False,"lot_size_history_available":False},"scenarios":scenarios,"regimes":regime,"calendar_years":years,"positive_regime_rate":positive_regime_rate,"positive_calendar_year_rate":positive_year_rate,"gate_reasons":reasons,"next_gate":not reasons,"promotion_status":"RESEARCH_ONLY_NO_LIVE_TRADING","elapsed_seconds":round(time.time()-start,2)}
    Path(a.out).write_text(json.dumps(result,indent=2)); print(json.dumps({"events":len(events),"positive_regime_rate":positive_regime_rate,"positive_calendar_year_rate":positive_year_rate,"gate_reasons":reasons,"next_gate":not reasons,"out":a.out,"elapsed_seconds":result["elapsed_seconds"]},indent=2),flush=True)

if __name__=="__main__": main()
