from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import time
from collections import Counter, defaultdict
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


def build_events(rows, family, cond, horizon, total_cost_bps):
    e = enrich(rows)
    out = []
    for i, r in enumerate(e):
        if not match(r, cond):
            continue
        entry_i, exit_i = i + 1, i + 1 + horizon
        if exit_i >= len(e):
            continue
        signal_ts = int(r["timestamp"])
        entry = e[entry_i]
        exit_ = e[exit_i]
        entry_ts = int(entry["timestamp"])
        exit_ts = int(exit_["timestamp"])
        ep = float(entry.get("open") or 0)
        xp = float(exit_.get("close") or 0)
        if ep <= 0 or xp < 0 or not (signal_ts < entry_ts < exit_ts):
            continue
        ret = max(xp / ep - 1 - total_cost_bps / 10000, -1)
        out.append({
            "signal_timestamp": signal_ts,
            "entry_timestamp": entry_ts,
            "exit_timestamp": exit_ts,
            "return": ret,
            "family": family,
            "strike_key": r["strike_key"],
            "side": r["side"],
            "signal_close": float(r.get("close") or 0),
            "entry_open": ep,
            "exit_close": xp,
            "signal_volume": float(r.get("volume") or 0),
            "entry_volume": float(entry.get("volume") or 0),
            "signal_oi": float(r.get("oi") or 0),
            "entry_oi": float(entry.get("oi") or 0),
            "signal_iv": float(r.get("iv") or 0),
            "entry_iv": float(entry.get("iv") or 0),
            "signal_spot": float(r.get("spot") or 0),
            "entry_spot": float(entry.get("spot") or 0),
            "regime": r["regime"],
        })
    return out


def simulate(events, initial, alloc, maxpos):
    by = defaultdict(list)
    for e in events:
        by[e["entry_timestamp"]].append(e)
    target = initial * alloc
    cash = initial
    active = []
    done = []
    peak = initial
    dd = 0.0
    for ts in sorted(by):
        for p in list(active):
            if p["exit_timestamp"] <= ts:
                cash += p["position_value"] + p["pnl"]
                done.append(p)
                active.remove(p)
        if len(active) < maxpos and cash >= target:
            for c in sorted(by[ts], key=lambda x: (x["family"], x["strike_key"])):
                if len(active) >= maxpos:
                    break
                cash -= target
                active.append({**c, "position_value": target, "pnl": target * c["return"]})
        equity = cash + sum(p["position_value"] + p["pnl"] for p in active)
        peak = max(peak, equity)
        dd = min(dd, equity / peak - 1)
    for p in active:
        cash += p["position_value"] + p["pnl"]
        done.append(p)
    pnls = [p["pnl"] for p in done]
    gross_win = sum(x for x in pnls if x > 0)
    gross_loss = -sum(x for x in pnls if x < 0)
    pf = gross_win / gross_loss if gross_loss else (float("inf") if gross_win else None)
    return {"trades": len(done), "return": sum(pnls) / initial if initial else 0, "profit_factor": pf, "drawdown": dd}


def pct(x):
    return f"{x:.2%}"


def main():
    p = argparse.ArgumentParser(description="V20 signal integrity and trade lifecycle audit")
    p.add_argument("--db", default="data/research/market_data.sqlite")
    p.add_argument("--input", default="data/research/option_family_v6.json")
    p.add_argument("--out", default="data/research/option_family_v20.json")
    p.add_argument("--horizon", type=int, default=6)
    p.add_argument("--cost-bps", type=float, default=5)
    p.add_argument("--slippage-bps", type=float, default=5)
    p.add_argument("--initial-capital", type=float, default=100000)
    p.add_argument("--allocation-pct", type=float, default=.02)
    p.add_argument("--max-positions", type=int, default=5)
    a = p.parse_args()
    start = time.time()

    src = json.loads(Path(a.input).read_text())
    fams = [x for x in src.get("results", []) if x.get("eligible_for_next_research_gate")]
    if not fams:
        raise SystemExit("V20 requires V6 eligible families.")

    db = sqlite3.connect(a.db)
    db.row_factory = sqlite3.Row
    cols = {r["name"] for r in db.execute("PRAGMA table_info(option_bars)")}
    required = {"timestamp", "side", "strike_key", "open", "high", "low", "close", "volume", "oi", "iv", "spot", "contract_identity"}
    missing = required - cols
    if missing:
        raise SystemExit(f"Missing required columns: {sorted(missing)}")
    total, identities, null_contract = db.execute("SELECT COUNT(*),COUNT(contract_identity),SUM(CASE WHEN contract_identity IS NULL OR contract_identity='' THEN 1 ELSE 0 END) FROM option_bars").fetchone()
    if total != identities or null_contract:
        raise SystemExit(f"Incomplete contract identity: {identities}/{total}, null={null_contract}")

    specs = set()
    for f in fams:
        side, cond = family_sig(f["family"])
        for n in f.get("matched_candidate_names", []):
            s, strike, cc = parse_name(n)
            if s == side and cc == cond:
                specs.add((s, strike))

    groups = {}
    for s, k in sorted(specs):
        groups[(s, k)] = [dict(r) for r in db.execute(
            "SELECT timestamp,side,strike_key,contract_identity,open,high,low,close,volume,oi,iv,spot FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp",
            (s, k)
        )]
    db.close()

    total_cost = a.cost_bps + a.slippage_bps
    events = []
    for f in fams:
        family = f["family"]
        side, cond = family_sig(family)
        for n in f.get("matched_candidate_names", []):
            s, k, cc = parse_name(n)
            if s == side and cc == cond:
                events.extend(build_events(groups.get((s, k), []), family, cond, a.horizon, total_cost))
    events.sort(key=lambda x: (x["entry_timestamp"], x["family"], x["strike_key"]))
    if not events:
        raise SystemExit("V20 generated zero events.")

    # 1. Signal/entry/exit lifecycle integrity.
    bad_order = [e for e in events if not (e["signal_timestamp"] < e["entry_timestamp"] < e["exit_timestamp"])]
    same_ts_signal_entry = [e for e in events if e["signal_timestamp"] == e["entry_timestamp"]]
    duplicate_identity = Counter((e["signal_timestamp"], e["family"], e["strike_key"]) for e in events)
    duplicate_events = sum(v - 1 for v in duplicate_identity.values() if v > 1)
    nonpositive_prices = [e for e in events if e["entry_open"] <= 0 or e["exit_close"] < 0]
    future_reference = [e for e in events if e["entry_timestamp"] <= e["signal_timestamp"] or e["exit_timestamp"] <= e["entry_timestamp"]]

    # 2. Timestamp/bar spacing checks. Expected 5-minute bars; report deviations rather than silently discarding them.
    entry_gaps = []
    exit_gaps = []
    for e in events:
        entry_gaps.append(e["entry_timestamp"] - e["signal_timestamp"])
        exit_gaps.append(e["exit_timestamp"] - e["entry_timestamp"])
    expected_bar = 300
    bad_entry_spacing = sum(x != expected_bar for x in entry_gaps)
    bad_exit_spacing = sum(x != expected_bar * a.horizon for x in exit_gaps)

    # 3. Per-day signal density and overlapping lifecycle checks.
    by_day = defaultdict(int)
    by_entry = defaultdict(int)
    for e in events:
        by_day[e["entry_timestamp"] // 86400] += 1
        by_entry[e["entry_timestamp"]] += 1
    daily_counts = list(by_day.values())
    entry_collision_timestamps = sum(1 for v in by_entry.values() if v > 1)

    # 4. Family/side distribution and P&L concentration.
    family_counts = Counter(e["family"] for e in events)
    side_counts = Counter(e["side"] for e in events)
    family_returns = defaultdict(float)
    for e in events:
        family_returns[e["family"]] += e["return"]
    ranked = sorted(family_returns.items(), key=lambda x: x[1], reverse=True)
    total_positive_family_return = sum(v for _, v in ranked if v > 0)
    top_family_return_share = ranked[0][1] / total_positive_family_return if ranked and total_positive_family_return > 0 else 0

    # 5. Distribution / loss-tail diagnostics.
    rets = sorted(e["return"] for e in events)
    wins = [x for x in rets if x > 0]
    losses = [x for x in rets if x < 0]
    mean_ret = statistics.mean(rets)
    median_ret = statistics.median(rets)
    p05 = rets[max(0, int(.05 * len(rets)) - 1)]
    p95 = rets[min(len(rets) - 1, int(.95 * len(rets)))]
    worst_20 = rets[:min(20, len(rets))]
    best_20 = rets[-min(20, len(rets)):]
    consecutive_losses = 0
    max_consecutive_losses = 0
    # chronological event returns, not portfolio sequencing
    for e in events:
        if e["return"] < 0:
            consecutive_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        else:
            consecutive_losses = 0

    # 6. Entry/exit liquidity and data sanity. This is deliberately descriptive: no arbitrary filter is applied.
    zero_entry_volume = sum(e["entry_volume"] <= 0 for e in events)
    zero_entry_oi = sum(e["entry_oi"] <= 0 for e in events)
    invalid_iv = sum(e["entry_iv"] < 0 for e in events)
    invalid_spot = sum(e["entry_spot"] <= 0 for e in events)
    nonfinite_values = sum(not all(map(lambda x: isinstance(x, (int, float)) and x == x and abs(x) != float("inf"), [e["entry_open"], e["exit_close"], e["return"]])) for e in events)

    # 7. Baseline portfolio and conservative one-bar execution reference.
    baseline = simulate(events, a.initial_capital, a.allocation_pct, a.max_positions)
    next_open_events = [e for e in events if e["signal_timestamp"] + expected_bar == e["entry_timestamp"]]
    next_open = simulate(next_open_events, a.initial_capital, a.allocation_pct, a.max_positions)

    reasons = []
    if bad_order or same_ts_signal_entry or future_reference:
        reasons.append("lifecycle_timestamp_failure")
    if duplicate_events:
        reasons.append("duplicate_signal_failure")
    if nonpositive_prices or nonfinite_values:
        reasons.append("price_numeric_failure")
    if invalid_spot:
        reasons.append("spot_data_failure")
    if invalid_iv:
        reasons.append("iv_data_failure")
    if bad_entry_spacing > len(events) * .05 or bad_exit_spacing > len(events) * .05:
        reasons.append("bar_spacing_failure")
    if zero_entry_volume > len(events) * .10:
        reasons.append("entry_volume_quality_failure")
    if baseline["trades"] < 1000 or (baseline["profit_factor"] or 0) < 1.05:
        reasons.append("baseline_execution_failure")
    if next_open["trades"] < 1000 or (next_open["profit_factor"] or 0) < 1.05:
        reasons.append("next_open_reference_failure")

    result = {
        "version": "v20",
        "purpose": "signal timestamp, execution lifecycle, duplicate, bar-spacing, data-quality and trade-distribution audit",
        "events": len(events),
        "data_quality": {
            "option_bar_rows": total,
            "contract_identity_complete": total == identities and null_contract == 0,
            "null_contract_identity": int(null_contract or 0),
            "zero_entry_volume": zero_entry_volume,
            "zero_entry_oi": zero_entry_oi,
            "invalid_iv": invalid_iv,
            "invalid_spot": invalid_spot,
            "nonfinite_values": nonfinite_values,
        },
        "lifecycle": {
            "bad_order_events": len(bad_order),
            "same_timestamp_signal_entry": len(same_ts_signal_entry),
            "future_reference_events": len(future_reference),
            "duplicate_events": duplicate_events,
            "entry_collision_timestamps": entry_collision_timestamps,
            "bad_entry_spacing": bad_entry_spacing,
            "bad_exit_spacing": bad_exit_spacing,
            "expected_bar_seconds": expected_bar,
            "horizon_bars": a.horizon,
        },
        "distribution": {
            "mean_return": mean_ret,
            "median_return": median_ret,
            "p05_return": p05,
            "p95_return": p95,
            "win_rate": len(wins) / len(rets),
            "loss_rate": len(losses) / len(rets),
            "max_consecutive_losses": max_consecutive_losses,
            "worst_20_mean": statistics.mean(worst_20) if worst_20 else None,
            "best_20_mean": statistics.mean(best_20) if best_20 else None,
        },
        "signal_density": {
            "trading_days": len(daily_counts),
            "median_events_per_day": statistics.median(daily_counts) if daily_counts else 0,
            "max_events_per_day": max(daily_counts) if daily_counts else 0,
            "median_events_per_entry_timestamp": statistics.median(list(by_entry.values())) if by_entry else 0,
        },
        "composition": {
            "family_counts": dict(sorted(family_counts.items())),
            "side_counts": dict(side_counts),
            "top_family_positive_return_share": top_family_return_share,
            "family_return_ranking": ranked,
        },
        "execution_reference": {
            "total_cost_bps": total_cost,
            "baseline": baseline,
            "strict_next_bar_open_subset": {"events": len(next_open_events), **next_open},
        },
        "gate_reasons": reasons,
        "next_gate": not reasons,
        "promotion_status": "RESEARCH_ONLY_NO_LIVE_TRADING",
        "elapsed_seconds": round(time.time() - start, 2),
        "data_range": {
            "start": datetime.fromtimestamp(events[0]["signal_timestamp"], tz=timezone.utc).isoformat(),
            "end": datetime.fromtimestamp(events[-1]["exit_timestamp"], tz=timezone.utc).isoformat(),
        },
    }
    Path(a.out).write_text(json.dumps(result, indent=2))
    print(f"OPTION FAMILY V20: events={len(events)} bad_order={len(bad_order)} duplicates={duplicate_events} bad_spacing_entry={bad_entry_spacing} bad_spacing_exit={bad_exit_spacing}", flush=True)
    print(f"OPTION FAMILY V20: baseline trades={baseline['trades']} return={pct(baseline['return'])} PF={baseline['profit_factor']} DD={pct(baseline['drawdown'])}", flush=True)
    print(f"OPTION FAMILY V20: next_bar_open_subset events={len(next_open_events)} trades={next_open['trades']} return={pct(next_open['return'])} PF={next_open['profit_factor']} DD={pct(next_open['drawdown'])}", flush=True)
    print(json.dumps({"events": len(events), "gate_reasons": reasons, "next_gate": not reasons, "out": a.out, "elapsed_seconds": result["elapsed_seconds"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
