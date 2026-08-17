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
    cond = tuple(sorted(x for x in raw.split("+") if x and x != "base"))
    return side, cond


def enrich(rows):
    rows = sorted(rows, key=lambda r: r["timestamp"])
    if not rows:
        return []
    closes = [float(r["close"]) for r in rows]
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
        })
    return out


def stats(events, initial=100000, alloc=.02, maxpos=5):
    by = defaultdict(list)
    for e in events:
        by[e["entry_timestamp"]].append(e)
    fixed = initial * alloc
    cash = initial
    active = []
    done = []
    peak = initial
    dd = 0.0
    skipped = 0
    maxexp = 0.0
    for ts in sorted(by):
        keep = []
        for p in active:
            if p["exit_timestamp"] <= ts:
                cash += p["value"] + p["pnl"]
                done.append(p)
            else:
                keep.append(p)
        active = keep
        used = sum(p["value"] for p in active)
        candidates = sorted(by[ts], key=lambda x: (x["family"], x["strike_key"]))
        if not candidates or len(active) >= maxpos or used + fixed > initial or cash < fixed:
            skipped += 1
        else:
            c = candidates[0]
            cash -= fixed
            active.append({**c, "value": fixed, "pnl": fixed * c["return"]})
            maxexp = max(maxexp, (used + fixed) / initial)
        equity = cash + sum(p["value"] + p["pnl"] for p in active)
        peak = max(peak, equity)
        dd = min(dd, equity / peak - 1) if peak else dd
    for p in sorted(active, key=lambda x: x["exit_timestamp"]):
        cash += p["value"] + p["pnl"]
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
    }


def chronological_folds(events, folds):
    timestamps = sorted({e["signal_timestamp"] for e in events})
    if not timestamps:
        return []
    n = min(max(1, folds), len(timestamps))
    result = []
    for i in range(n):
        start_idx = (i * len(timestamps)) // n
        end_idx = ((i + 1) * len(timestamps)) // n
        if end_idx <= start_idx:
            continue
        lo = timestamps[start_idx]
        hi = timestamps[end_idx - 1]
        result.append((i + 1, lo, hi))
    return result


def main():
    p = argparse.ArgumentParser(description="V16 next-bar-open robustness, strict holdout and family stability audit")
    p.add_argument("--db", default="data/research/market_data.sqlite")
    p.add_argument("--input", default="data/research/option_family_v6.json")
    p.add_argument("--out", default="data/research/option_family_v16.json")
    p.add_argument("--horizon", type=int, default=6)
    p.add_argument("--cost-bps", type=float, default=5)
    p.add_argument("--slippage-bps", type=float, default=5)
    p.add_argument("--initial-capital", type=float, default=100000)
    p.add_argument("--allocation-pct", type=float, default=.02)
    p.add_argument("--max-positions", type=int, default=5)
    p.add_argument("--folds", type=int, default=4)
    a = p.parse_args()
    start = time.time()

    src = json.loads(Path(a.input).read_text())
    fam = [r for r in src.get("results", []) if r.get("eligible_for_next_research_gate")]
    if not fam:
        raise SystemExit("V16 requires V6 eligible families.")

    db = sqlite3.connect(a.db)
    db.row_factory = sqlite3.Row
    cols = {r["name"] for r in db.execute("PRAGMA table_info(option_bars)")}
    required = {"timestamp", "side", "strike_key", "open", "close", "volume", "oi", "iv"}
    missing = required - cols
    if missing:
        raise SystemExit(f"Missing required columns: {sorted(missing)}")
    if "contract_identity" not in cols:
        raise SystemExit("V16 requires contract_identity")
    total, identity = db.execute("SELECT COUNT(*), COUNT(contract_identity) FROM option_bars").fetchone()
    if total != identity:
        raise SystemExit(f"Incomplete contract identity: {identity}/{total}")

    specs = sorted({(parse_name(n)[0], parse_name(n)[1]) for f in fam for n in f.get("matched_candidate_names", [])})
    if not specs:
        raise SystemExit("V16 found no matched_candidate_names in eligible V6 families")

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
        raise SystemExit("V16 generated zero events. Check V6 matched_candidate_names, family naming, and option-bar coverage; no fold calculation was attempted.")

    timestamps = sorted({e["signal_timestamp"] for e in events})
    cutoff = timestamps[max(0, int(len(timestamps) * .8) - 1)]
    hold = [e for e in events if e["signal_timestamp"] > cutoff]
    overall = stats(events, a.initial_capital, a.allocation_pct, a.max_positions)
    strict = stats(hold, a.initial_capital, a.allocation_pct, a.max_positions)

    fold_defs = chronological_folds(events, a.folds)
    folds = []
    for number, lo, hi in fold_defs:
        fe = [e for e in events if lo <= e["signal_timestamp"] <= hi]
        r = stats(fe, a.initial_capital, a.allocation_pct, a.max_positions)
        folds.append({"fold": number, "start": lo, "end": hi, **r})

    family_results = []
    for name in [f["family"] for f in fam]:
        ev = [e for e in events if e["family"] == name]
        r = stats(ev, a.initial_capital, a.allocation_pct, min(a.max_positions, 3))
        family_results.append({"family": name, **r, "event_share": len(ev) / len(events)})

    positive = sum(1 for f in folds if f["profit_factor"] is not None and f["profit_factor"] > 1.05)
    positive_rate = positive / len(folds) if folds else 0
    reasons = []
    if strict["profit_factor"] is None or strict["profit_factor"] < 1.10 or strict["return_pct"] <= 0:
        reasons.append("strict_holdout_failure")
    if not folds or positive < len(folds):
        reasons.append("fold_instability")
    if any(f["event_share"] > .80 for f in family_results):
        reasons.append("family_concentration")

    result = {
        "version": "v16",
        "purpose": "next-bar-open robustness, strict holdout and family stability",
        "execution": "signal at completed bar close; entry at next bar open; exit at horizon-bar close",
        "cost_bps_round_trip": cost,
        "events": len(events),
        "timestamp_count": len(timestamps),
        "overall": overall,
        "strict_holdout": strict,
        "folds": folds,
        "family_results": family_results,
        "positive_fold_rate": positive_rate,
        "gate_reasons": reasons,
        "next_gate": not reasons,
        "promotion_status": "RESEARCH_ONLY_NO_PAPER_TRADING",
        "elapsed_seconds": round(time.time() - start, 2),
    }
    Path(a.out).write_text(json.dumps(result, indent=2))
    print(json.dumps({
        "events": len(events),
        "timestamps": len(timestamps),
        "strict_holdout_pf": strict["profit_factor"],
        "strict_holdout_return": strict["return_pct"],
        "positive_fold_rate": positive_rate,
        "gate_reasons": reasons,
        "next_gate": result["next_gate"],
        "out": a.out,
        "elapsed_seconds": result["elapsed_seconds"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
