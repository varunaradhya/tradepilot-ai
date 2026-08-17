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
    closes = [float(r["close"] or 0) for r in rows]
    ema20, ema50 = [], []
    a = b = closes[0]
    for x in closes:
        a = x * (2 / 21) + a * (19 / 21)
        b = x * (2 / 51) + b * (49 / 51)
        ema20.append(a)
        ema50.append(b)
    out = []
    for i, r in enumerate(rows):
        prior = rows[max(0, i - 20):i]
        avg = sum(float(x.get("volume") or 0) for x in prior) / max(1, len(prior))
        out.append({
            **r,
            "ema20": ema20[i],
            "ema50": ema50[i],
            "rel_volume": float(r.get("volume") or 0) / avg if avg else 0,
        })
    return out


def condition_match(r, cond):
    for c in cond:
        if c == "premium_trend" and not r["ema20"] > r["ema50"]:
            return False
        if c == "premium_weak" and not r["ema20"] < r["ema50"]:
            return False
        if c == "relvol_1_5" and not r["rel_volume"] >= 1.5:
            return False
        if c == "iv_high" and not float(r.get("iv") or 0) > 20:
            return False
        if c == "iv_low" and not 0 < float(r.get("iv") or 0) < 15:
            return False
        if c == "oi_present" and not float(r.get("oi") or 0) > 0:
            return False
    return True


def build_events(rows, family, cond, horizon, cost_bps):
    e = enrich(rows)
    out = []
    for i in range(len(e)):
        if not condition_match(e[i], cond):
            continue
        entry_i = i + 1
        exit_i = entry_i + horizon
        if exit_i >= len(e):
            continue
        entry_price = float(e[entry_i].get("open") or 0)
        exit_price = float(e[exit_i].get("close") or 0)
        volume = float(e[entry_i].get("volume") or 0)
        oi = float(e[entry_i].get("oi") or 0)
        if entry_price <= 0 or exit_price < 0:
            continue
        ret = max(exit_price / entry_price - 1 - cost_bps / 10000, -1)
        out.append({
            "signal_timestamp": e[i]["timestamp"],
            "entry_timestamp": e[entry_i]["timestamp"],
            "exit_timestamp": e[exit_i]["timestamp"],
            "return": ret,
            "family": family,
            "strike_key": e[i]["strike_key"],
            "entry_price": entry_price,
            "entry_volume": volume,
            "entry_oi": oi,
        })
    return out


def simulate(events, initial, alloc, maxpos, participation, min_volume, min_oi, min_premium):
    by = defaultdict(list)
    for e in events:
        by[e["entry_timestamp"]].append(e)
    target = initial * alloc
    cash = initial
    active = []
    done = []
    skipped = 0
    filtered = 0
    maxexp = 0.0
    peak = initial
    dd = 0.0

    for ts in sorted(by):
        keep = []
        for p in active:
            if p["exit_timestamp"] <= ts:
                cash += p["position_value"] + p["pnl"]
                done.append(p)
            else:
                keep.append(p)
        active = keep
        used = sum(p["position_value"] for p in active)
        candidates = []
        for e in by[ts]:
            if e["entry_volume"] < min_volume or e["entry_oi"] < min_oi or e["entry_price"] < min_premium:
                filtered += 1
                continue
            candidates.append(e)
        candidates.sort(key=lambda x: (x["family"], x["strike_key"]))

        if not candidates or len(active) >= maxpos or used + target > initial or cash < target:
            skipped += 1
        else:
            c = candidates[0]
            # Dynamic position value: never assume we can consume more than the
            # configured fraction of the observed entry-bar volume. This is a
            # tradeability proxy, not a broker execution guarantee.
            volume_capacity = c["entry_volume"] * c["entry_price"] * participation
            position_value = min(target, volume_capacity)
            if position_value <= 0:
                filtered += 1
            else:
                cash -= position_value
                active.append({**c, "position_value": position_value, "pnl": position_value * c["return"]})
                maxexp = max(maxexp, (used + position_value) / initial)

        equity = cash + sum(p["position_value"] + p["pnl"] for p in active)
        peak = max(peak, equity)
        if peak:
            dd = min(dd, equity / peak - 1)

    for p in sorted(active, key=lambda x: x["exit_timestamp"]):
        cash += p["position_value"] + p["pnl"]
        done.append(p)

    pnls = [p["pnl"] for p in done]
    vals = [p["return"] for p in done]
    wins = [x for x in pnls if x > 0]
    losses = [-x for x in pnls if x < 0]
    pf = sum(wins) / sum(losses) if losses else (float("inf") if wins else None)
    return {
        "trades": len(done),
        "expectancy": statistics.mean(vals) if vals else 0,
        "profit_factor": pf,
        "return_pct": sum(pnls) / initial if initial else 0,
        "max_drawdown_pct": dd,
        "max_exposure_pct": maxexp,
        "skipped": skipped,
        "liquidity_filtered_events": filtered,
        "average_position_value": statistics.mean([p["position_value"] for p in done]) if done else 0,
        "median_position_value": statistics.median([p["position_value"] for p in done]) if done else 0,
    }


def main():
    p = argparse.ArgumentParser(description="V17 realistic liquidity and position-sizing audit")
    p.add_argument("--db", default="data/research/market_data.sqlite")
    p.add_argument("--input", default="data/research/option_family_v6.json")
    p.add_argument("--out", default="data/research/option_family_v17.json")
    p.add_argument("--horizon", type=int, default=6)
    p.add_argument("--cost-bps", type=float, default=5)
    p.add_argument("--slippage-bps", type=float, default=5)
    p.add_argument("--initial-capital", type=float, default=100000)
    p.add_argument("--allocation-pct", type=float, default=.02)
    p.add_argument("--max-positions", type=int, default=5)
    a = p.parse_args()
    start = time.time()

    src = json.loads(Path(a.input).read_text())
    fam = [r for r in src.get("results", []) if r.get("eligible_for_next_research_gate")]
    if not fam:
        raise SystemExit("V17 requires V6 eligible families.")

    db = sqlite3.connect(a.db)
    db.row_factory = sqlite3.Row
    cols = {r["name"] for r in db.execute("PRAGMA table_info(option_bars)")}
    required = {"timestamp", "side", "strike_key", "open", "close", "volume", "oi", "iv", "contract_identity"}
    missing = required - cols
    if missing:
        raise SystemExit(f"Missing required columns: {sorted(missing)}")
    total, identity = db.execute("SELECT COUNT(*), COUNT(contract_identity) FROM option_bars").fetchone()
    if total != identity:
        raise SystemExit(f"Incomplete contract identity: {identity}/{total}")

    specs = sorted({(parse_name(n)[0], parse_name(n)[1]) for f in fam for n in f.get("matched_candidate_names", [])})
    groups = {}
    for side, strike in specs:
        groups[(side, strike)] = [dict(r) for r in db.execute(
            "SELECT timestamp,side,strike_key,open,close,volume,oi,iv FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp",
            (side, strike),
        )]
    db.close()

    cost = a.cost_bps + a.slippage_bps
    events = []
    for f in fam:
        family = f["family"]
        side, cond = family_sig(family)
        for candidate in f.get("matched_candidate_names", []):
            cs, strike, cc = parse_name(candidate)
            if cs == side and cc == cond:
                events.extend(build_events(groups.get((cs, strike), []), family, cond, a.horizon, cost))
    events.sort(key=lambda x: (x["signal_timestamp"], x["family"], x["strike_key"]))
    if not events:
        raise SystemExit("V17 generated zero events. Check V6 family definitions and option-bar coverage.")

    scenarios = []
    # The 1% participation case is the primary conservative proxy. 2% and 5%
    # show sensitivity. No scenario claims actual fillability without bid/ask data.
    for participation in (0.01, 0.02, 0.05):
        for min_volume in (0, 1000, 5000):
            r = simulate(events, a.initial_capital, a.allocation_pct, a.max_positions,
                          participation, min_volume, 0, 0)
            scenarios.append({
                "name": f"participation_{participation:.0%}_minvol_{min_volume}",
                "participation": participation,
                "min_volume": min_volume,
                "min_oi": 0,
                "min_premium": 0,
                **r,
            })
            print(f"OPTION FAMILY V17: participation={participation:.0%} minvol={min_volume} trades={r['trades']} return={r['return_pct']:.2%} PF={r['profit_factor']} DD={r['max_drawdown_pct']:.2%} exposure={r['max_exposure_pct']:.2%} filtered={r['liquidity_filtered_events']}", flush=True)

    # Premium/interest filters test whether apparent edge is concentrated in tiny,
    # low-quality contracts. These are diagnostics rather than hard requirements.
    for min_premium in (5, 10, 20):
        r = simulate(events, a.initial_capital, a.allocation_pct, a.max_positions,
                     0.01, 0, 0, min_premium)
        scenarios.append({"name": f"participation_1%_minpremium_{min_premium}",
                          "participation": .01, "min_volume": 0, "min_oi": 0,
                          "min_premium": min_premium, **r})
        print(f"OPTION FAMILY V17: participation=1% minpremium={min_premium} trades={r['trades']} return={r['return_pct']:.2%} PF={r['profit_factor']} DD={r['max_drawdown_pct']:.2%} exposure={r['max_exposure_pct']:.2%} filtered={r['liquidity_filtered_events']}", flush=True)

    primary = next(x for x in scenarios if x["name"] == "participation_1%_minvol_1000")
    stress = next(x for x in scenarios if x["name"] == "participation_1%_minvol_5000")
    reasons = []
    if primary["trades"] < 1000 or primary["profit_factor"] is None or primary["profit_factor"] < 1.05 or primary["return_pct"] <= 0:
        reasons.append("primary_liquidity_failure")
    if stress["trades"] < 500 or stress["profit_factor"] is None or stress["profit_factor"] < 1.00 or stress["return_pct"] <= 0:
        reasons.append("stress_liquidity_failure")

    result = {
        "version": "v17",
        "purpose": "realistic liquidity and dynamic position-sizing audit after V14 execution failure",
        "methodology": {
            "entry": "next bar open after completed-bar signal",
            "exit": "horizon-bar close",
            "round_trip_cost_bps": cost,
            "position_sizing": "target allocation capped by participation fraction of entry-bar traded volume times entry price",
            "important_limitation": "Volume is a tradeability proxy. Without bid/ask and lot-size history this is not an execution guarantee.",
        },
        "data_quality": {
            "option_bar_rows": total,
            "contract_identity_complete": total == identity,
            "bid_ask_available": False,
            "lot_size_history_available": False,
        },
        "events": len(events),
        "scenarios": scenarios,
        "primary": primary,
        "stress": stress,
        "gate_reasons": reasons,
        "next_gate": not reasons,
        "promotion_status": "RESEARCH_ONLY_NO_PAPER_TRADING",
        "elapsed_seconds": round(time.time() - start, 2),
    }
    Path(a.out).write_text(json.dumps(result, indent=2))
    print(json.dumps({
        "events": len(events),
        "primary_trades": primary["trades"],
        "primary_pf": primary["profit_factor"],
        "primary_return": primary["return_pct"],
        "stress_trades": stress["trades"],
        "stress_pf": stress["profit_factor"],
        "gate_reasons": reasons,
        "next_gate": result["next_gate"],
        "out": a.out,
        "elapsed_seconds": result["elapsed_seconds"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
