from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.strategy_validation import _drawdown, _stats


def parse_name(name):
    parts = name.split(":")
    side = parts[0]
    strike = parts[1] if len(parts) > 1 else ""
    conditions = tuple(sorted(c for c in (parts[2].split("+") if len(parts) > 2 else []) if c))
    return side, strike, conditions


def family_signature(name):
    parts = name.split(":")
    side = parts[0]
    conditions = parts[2].split("+") if len(parts) >= 3 else []
    return side, tuple(sorted(c for c in conditions if c and c != "base"))


def enrich(rows):
    rows = sorted(rows, key=lambda r: r["timestamp"])
    if not rows:
        return []
    closes = [float(r["close"]) for r in rows]
    k20, k50 = 2 / 21, 2 / 51
    e20, e50 = [], []
    a = b = closes[0]
    for c in closes:
        a = c * k20 + a * (1 - k20)
        b = c * k50 + b * (1 - k50)
        e20.append(a)
        e50.append(b)
    out = []
    for i, r in enumerate(rows):
        start = max(0, i - 20)
        avg = sum(float(x.get("volume") or 0) for x in rows[start:i]) / max(i - start, 1)
        out.append({**r, "ema20": e20[i], "ema50": e50[i], "rel_volume": float(r.get("volume") or 0) / avg if avg else 0})
    return out


def signal(row, conditions):
    for c in conditions:
        if c == "premium_trend" and not row["ema20"] > row["ema50"]:
            return False
        if c == "premium_weak" and not row["ema20"] < row["ema50"]:
            return False
        if c == "relvol_1_5" and not row["rel_volume"] >= 1.5:
            return False
        if c == "iv_high" and not float(row.get("iv") or 0) > 20:
            return False
        if c == "iv_low" and not 0 < float(row.get("iv") or 0) < 15:
            return False
        if c == "oi_present" and not float(row.get("oi") or 0) > 0:
            return False
    return True


def returns_for(rows, conditions, horizon, friction):
    enriched = enrich(rows)
    out = []
    for i in range(len(enriched) - horizon):
        if signal(enriched[i], conditions):
            entry = float(enriched[i]["close"])
            exit_ = float(enriched[i + horizon]["close"])
            if entry > 0:
                out.append((enriched[i]["timestamp"], exit_ / entry - 1 - friction))
    return out


def metric(values):
    vals = [x[1] for x in values]
    n, expectancy, win_rate, pf, total_return = _stats(vals)
    return {"trades": n, "expectancy": expectancy, "win_rate": win_rate, "profit_factor": pf, "return": total_return, "drawdown": _drawdown(vals)}


def family_fold_metrics(family, candidates, groups, timestamps, horizon, friction):
    side, conditions = family_signature(family)
    fold_returns = [[] for _ in timestamps]
    for c in candidates:
        cside, strike, cconditions = parse_name(c["name"])
        if cside != side or cconditions != conditions:
            continue
        rr = returns_for(groups.get((cside, strike), []), conditions, horizon, friction)
        for ts, value in rr:
            for idx, (start, end, is_last) in enumerate(timestamps):
                if start <= ts < end or (is_last and ts == end):
                    fold_returns[idx].append((ts, value))
                    break
    result = []
    for values in fold_returns:
        by_ts = {}
        for ts, value in values:
            by_ts.setdefault(ts, []).append(value)
        combined = [(ts, statistics.median(v)) for ts, v in sorted(by_ts.items())]
        result.append(metric(combined))
    return result


def make_folds(all_timestamps, count=4):
    unique = sorted(set(all_timestamps))
    if not unique:
        return []
    count = max(1, min(int(count), len(unique)))
    folds = []
    n = len(unique)
    for i in range(count):
        lo = unique[(i * n) // count]
        hi = unique[((i + 1) * n) // count] if i < count - 1 else unique[-1]
        folds.append((lo, hi, i == count - 1))
    return folds


def main():
    p = argparse.ArgumentParser(description="V6 temporal stability and cost-sensitivity audit for V5 option families.")
    p.add_argument("--db", default="data/research/market_data.sqlite")
    p.add_argument("--input", default="data/research/option_family_v5.json")
    p.add_argument("--out", default="data/research/option_family_v6.json")
    p.add_argument("--horizon", type=int, default=6)
    p.add_argument("--cost-bps", type=float, default=5)
    p.add_argument("--slippage-bps", type=float, default=5)
    p.add_argument("--folds", type=int, default=4)
    a = p.parse_args()
    started = time.time()

    src = json.loads(Path(a.input).read_text(encoding="utf-8"))
    v5 = [r for r in src.get("results", []) if r.get("eligible_for_contract_gate")]
    if not v5:
        raise SystemExit("V6 requires at least one V5 contract-gate family. V5 produced none.")
    families = [r["family"] for r in v5]
    print(f"OPTION FAMILY V6: V5 eligible families={len(families)} {families}", flush=True)

    specs = []
    for r in v5:
        for name in r.get("matched_candidate_names", []):
            side, strike, _ = parse_name(name)
            specs.append((side, strike))
    specs = sorted(set(specs))

    db = sqlite3.connect(a.db)
    groups = {}
    all_ts = []
    try:
        for i, (side, strike) in enumerate(specs, 1):
            print(f"OPTION FAMILY V6: loading group {i}/{len(specs)} {side}:{strike}", flush=True)
            rows = [dict(zip(("timestamp", "side", "strike_key", "strike", "open", "high", "low", "close", "volume", "oi", "iv", "spot"), r)) for r in db.execute("SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp", (side, strike))]
            groups[(side, strike)] = rows
            all_ts.extend(r["timestamp"] for r in rows)
            if i % 3 == 0 or i == len(specs):
                print(f"OPTION FAMILY V6: loaded {i}/{len(specs)} groups elapsed={time.time()-started:.1f}s", flush=True)
    finally:
        db.close()

    folds = make_folds(all_ts, a.folds)
    print(f"OPTION FAMILY V6: folds={len(folds)}", flush=True)
    results = []
    for fi, family_row in enumerate(v5, 1):
        family = family_row["family"]
        print(f"OPTION FAMILY V6: family {fi}/{len(v5)} {family}", flush=True)
        candidates = [{"name": n} for n in family_row.get("matched_candidate_names", [])]
        sensitivity = {}
        for total_bps in (10.0, 15.0, 20.0):
            friction = total_bps / 10000.0
            fm = family_fold_metrics(family, candidates, groups, folds, a.horizon, friction)
            exps = [m["expectancy"] for m in fm if m["trades"]]
            pfs = [m["profit_factor"] for m in fm if m["profit_factor"] is not None]
            positive_folds = sum(x > 0 for x in exps)
            sensitivity[str(int(total_bps))] = {"friction_bps": total_bps, "folds": fm, "positive_fold_rate": positive_folds / len(exps) if exps else 0.0, "median_expectancy": statistics.median(exps) if exps else 0.0, "worst_expectancy": min(exps) if exps else 0.0, "worst_profit_factor": min(pfs) if pfs else None}
        base = sensitivity["10"]
        stress = sensitivity["15"]
        eligible = bool(base["positive_fold_rate"] >= 0.75 and base["worst_expectancy"] > 0 and base["worst_profit_factor"] is not None and base["worst_profit_factor"] >= 1.05 and stress["positive_fold_rate"] >= 0.75 and stress["median_expectancy"] > 0)
        reasons = []
        if base["positive_fold_rate"] < 0.75: reasons.append("unstable_positive_fold_rate")
        if base["worst_expectancy"] <= 0: reasons.append("negative_base_cost_fold")
        if base["worst_profit_factor"] is None or base["worst_profit_factor"] < 1.05: reasons.append("weak_base_cost_worst_pf")
        if stress["positive_fold_rate"] < 0.75 or stress["median_expectancy"] <= 0: reasons.append("cost_stress_failure")
        result = {"family": family, "eligible_for_next_research_gate": eligible, "rejection_reasons": reasons, "cost_sensitivity": sensitivity}
        results.append(result)
        print(f"OPTION FAMILY V6: {family} base10_median={base['median_expectancy']:.6f} worst={base['worst_expectancy']:.6f} worstPF={base['worst_profit_factor']} stress15_median={stress['median_expectancy']:.6f} positive15={stress['positive_fold_rate']:.2f} eligible={eligible} reasons={','.join(reasons) if reasons else 'NONE'}", flush=True)

    report = {"methodology": {"folds": len(folds), "horizon_bars": a.horizon, "base_friction_bps": 10.0, "stress_friction_bps": [15.0, 20.0], "selection_note": "V5 eligibility is fixed input; V6 is a temporal stability and cost-sensitivity audit, not a new discovery pass."}, "families": len(results), "next_gate_count": sum(r["eligible_for_next_research_gate"] for r in results), "results": results, "promotion_status": "RESEARCH_ONLY_NO_PAPER_TRADING", "critical_limit": "The underlying option cache is rolling strike-wise expired-options data; exact historical contract/expiry identity, bid-ask spread, fills and lot mechanics remain unvalidated.", "elapsed_seconds": round(time.time() - started, 2)}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"families": len(results), "next_gate": report["next_gate_count"], "elapsed_seconds": report["elapsed_seconds"], "out": a.out}, indent=2), flush=True)


if __name__ == "__main__":
    main()
