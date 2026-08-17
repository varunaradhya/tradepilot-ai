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
    cond = tuple(sorted(x for x in ((p[2].split("+") if len(p) > 2 else p[1].split("+") if len(p) == 2 else [])) if x and x != "base"))
    return side, cond


def enrich(rows):
    rows = sorted(rows, key=lambda r: r["timestamp"])
    if not rows:
        return []

    closes = [float(r["close"]) for r in rows]
    ema20 = []
    ema50 = []
    a = b = closes[0]
    k20, k50 = 2 / 21, 2 / 51
    for x in closes:
        a = x * k20 + a * (1 - k20)
        b = x * k50 + b * (1 - k50)
        ema20.append(a)
        ema50.append(b)

    out = []
    for i, r in enumerate(rows):
        prior = rows[max(0, i - 20):i]
        avg = sum(float(x.get("volume") or 0) for x in prior) / max(1, len(prior))
        close = float(r["close"])
        high = float(r.get("high") or close)
        low = float(r.get("low") or close)
        out.append({
            **r,
            "ema20": ema20[i],
            "ema50": ema50[i],
            "rel_volume": float(r.get("volume") or 0) / avg if avg else 0,
            "bar_range_pct": max(0, (high - low) / close) if close > 0 else 0,
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


def build_events(rows, family, cond, horizon, cost_bps, signal_lag, entry_mode):
    e = enrich(rows)
    out = []
    # signal_lag=0 means the signal uses the information available at bar i close.
    # signal_lag=1 means every signal feature is explicitly one bar old, allowing
    # a same-close entry without using the current bar's information.
    for i in range(len(e)):
        sig_i = i - signal_lag
        if sig_i < 0:
            continue

        if not condition_match(e[sig_i], cond):
            continue

        if entry_mode == "next_open":
            entry_i = i + 1
            if entry_i >= len(e):
                continue
            entry_price = float(e[entry_i].get("open") or 0)
            entry_ts = e[entry_i]["timestamp"]
            exit_i = entry_i + horizon
        elif entry_mode == "next_close":
            entry_i = i + 1
            if entry_i >= len(e):
                continue
            entry_price = float(e[entry_i]["close"])
            entry_ts = e[entry_i]["timestamp"]
            exit_i = entry_i + horizon
        elif entry_mode == "same_close_lagged":
            entry_i = i
            entry_price = float(e[entry_i]["close"])
            entry_ts = e[entry_i]["timestamp"]
            exit_i = entry_i + horizon
        elif entry_mode == "two_bar_open":
            entry_i = i + 2
            if entry_i >= len(e):
                continue
            entry_price = float(e[entry_i].get("open") or 0)
            entry_ts = e[entry_i]["timestamp"]
            exit_i = entry_i + horizon
        else:
            raise ValueError(f"Unknown entry_mode={entry_mode}")

        if exit_i >= len(e):
            continue
        exit_price = float(e[exit_i]["close"])
        if entry_price <= 0 or exit_price < 0:
            continue

        # Base round-trip friction is deliberately kept identical to the earlier gates.
        friction = cost_bps / 10000
        ret = max(exit_price / entry_price - 1 - friction, -1)
        out.append({
            "signal_timestamp": e[sig_i]["timestamp"],
            "entry_timestamp": entry_ts,
            "exit_timestamp": e[exit_i]["timestamp"],
            "return": ret,
            "family": family,
            "strike_key": e[sig_i]["strike_key"],
            "signal_rel_volume": e[sig_i]["rel_volume"],
            "entry_price": entry_price,
            "exit_price": exit_price,
        })
    return out


def simulate(events, initial, alloc, maxpos):
    by = defaultdict(list)
    for e in events:
        by[e["entry_timestamp"]].append(e)

    fixed = initial * alloc
    cash = initial
    active = []
    done = []
    skipped = 0
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
        candidates = sorted(by[ts], key=lambda x: (x["family"], x["strike_key"]))

        # One candidate per timestamp is the same conservative portfolio policy used by V10-V14.
        if not candidates or len(active) >= maxpos or used + fixed > initial or cash < fixed:
            skipped += 1
        else:
            c = candidates[0]
            cash -= fixed
            p = {**c, "position_value": fixed, "pnl": fixed * c["return"]}
            active.append(p)
            used += fixed
            maxexp = max(maxexp, used / initial)

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
        "win_rate": len(wins) / len(done) if done else 0,
        "expectancy": statistics.mean(vals) if vals else 0,
        "profit_factor": pf,
        "return_pct": sum(pnls) / initial if initial else 0,
        "max_drawdown_pct": dd,
        "max_exposure_pct": maxexp,
        "skipped": skipped,
    }


def main():
    p = argparse.ArgumentParser(description="V15 signal-timing and lookahead audit after V14 execution-realism failure.")
    p.add_argument("--db", default="data/research/market_data.sqlite")
    p.add_argument("--input", default="data/research/option_family_v6.json")
    p.add_argument("--out", default="data/research/option_family_v15.json")
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
        raise SystemExit("V15 requires V6 eligible families.")
    names = [r["family"] for r in fam]

    db = sqlite3.connect(a.db)
    db.row_factory = sqlite3.Row
    cols = [r["name"] for r in db.execute("PRAGMA table_info(option_bars)")]
    required = {"timestamp", "side", "strike_key", "open", "close", "high", "low", "volume", "oi", "iv"}
    missing = required - set(cols)
    if missing:
        raise SystemExit(f"Missing required columns: {sorted(missing)}")

    total, identity = db.execute("SELECT COUNT(*), COUNT(contract_identity) FROM option_bars").fetchone() if "contract_identity" in cols else (0, 0)
    if total and identity != total:
        raise SystemExit(f"V15 requires complete contract_identity coverage: {identity}/{total}")

    specs = sorted({(parse_name(n)[0], parse_name(n)[1]) for f in fam for n in f.get("matched_candidate_names", [])})
    groups = {}
    for side, strike in specs:
        groups[(side, strike)] = [dict(r) for r in db.execute(
            "SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot "
            "FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp",
            (side, strike),
        )]
    db.close()

    # cost-bps + slippage-bps is the same 10 bps round-trip base used in V14's baseline.
    base_cost_bps = a.cost_bps + a.slippage_bps
    scenarios = [
        {
            "name": "same_close_CURRENT_FEATURES",
            "entry_mode": "same_close_lagged",
            "signal_lag": 0,
            "cost_bps": base_cost_bps,
            "status": "INVALID_REFERENCE",
            "description": "Same-bar close entry using current-bar close-derived features; retained only to quantify the suspected lookahead-sensitive reference.",
        },
        {
            "name": "same_close_LAGGED_FEATURES",
            "entry_mode": "same_close_lagged",
            "signal_lag": 1,
            "cost_bps": base_cost_bps,
            "status": "REALISTIC_IF_SIGNAL_PRECOMPUTED",
            "description": "Enter at bar close using only the immediately previous bar's features.",
        },
        {
            "name": "next_bar_OPEN_CURRENT_FEATURES",
            "entry_mode": "next_open",
            "signal_lag": 0,
            "cost_bps": base_cost_bps,
            "status": "PRIMARY",
            "description": "Signal is formed from the completed bar; enter at the next bar open.",
        },
        {
            "name": "next_bar_CLOSE_CURRENT_FEATURES",
            "entry_mode": "next_close",
            "signal_lag": 0,
            "cost_bps": base_cost_bps,
            "status": "SECONDARY",
            "description": "Signal is formed from the completed bar; enter at the next bar close.",
        },
        {
            "name": "two_bar_OPEN_CURRENT_FEATURES",
            "entry_mode": "two_bar_open",
            "signal_lag": 0,
            "cost_bps": base_cost_bps,
            "status": "ROBUSTNESS",
            "description": "Two full bars between signal and entry to test timing decay.",
        },
    ]

    results = []
    for s in scenarios:
        events = []
        for f in fam:
            family = f["family"]
            side, cond = family_sig(family)
            for candidate in f.get("matched_candidate_names", []):
                cs, strike, cc = parse_name(candidate)
                if cs != side or cc != cond:
                    continue
                events.extend(build_events(
                    groups.get((cs, strike), []), family, cond, a.horizon,
                    s["cost_bps"], s["signal_lag"], s["entry_mode"],
                ))

        events.sort(key=lambda x: (x["entry_timestamp"], x["family"], x["strike_key"]))
        r = simulate(events, a.initial_capital, a.allocation_pct, a.max_positions)
        r.update({k: s[k] for k in ("name", "entry_mode", "signal_lag", "cost_bps", "status", "description")})
        results.append(r)
        print(
            f"OPTION FAMILY V15: {s['name']} trades={r['trades']} "
            f"return={r['return_pct']:.2%} PF={r['profit_factor']} "
            f"DD={r['max_drawdown_pct']:.2%} exposure={r['max_exposure_pct']:.2%} skipped={r['skipped']}",
            flush=True,
        )

    byname = {r["name"]: r for r in results}
    primary = byname["next_bar_OPEN_CURRENT_FEATURES"]
    lagged = byname["same_close_LAGGED_FEATURES"]
    invalid_ref = byname["same_close_CURRENT_FEATURES"]
    next_close = byname["next_bar_CLOSE_CURRENT_FEATURES"]
    two_bar = byname["two_bar_OPEN_CURRENT_FEATURES"]

    reasons = []
    # V15 is intentionally stricter than V14: the primary gate requires a positive
    # next-open PF with meaningful trade count and must not rely on same-bar current features.
    if primary["trades"] < 1000 or primary["profit_factor"] is None or primary["profit_factor"] < 1.05 or primary["return_pct"] <= 0:
        reasons.append("next_open_failure")
    if lagged["trades"] < 1000 or lagged["profit_factor"] is None or lagged["profit_factor"] < 1.05 or lagged["return_pct"] <= 0:
        reasons.append("lagged_feature_failure")
    if next_close["profit_factor"] is None or next_close["profit_factor"] < 1.05:
        reasons.append("next_close_failure")
    if two_bar["profit_factor"] is None or two_bar["profit_factor"] < 1.00:
        reasons.append("two_bar_timing_decay")

    # Flag suspicious dependence on same-bar execution rather than silently treating it as valid.
    if invalid_ref["profit_factor"] and primary["profit_factor"]:
        if invalid_ref["profit_factor"] > primary["profit_factor"] * 1.50:
            reasons.append("strong_same_bar_dependence")

    result = {
        "version": "v15",
        "purpose": "signal timing, lookahead and execution-delay audit after V14",
        "methodology": {
            "signal_definition": "Features are calculated from completed bars. Primary scenario generates the signal at bar close and enters at the next bar open.",
            "same_close_current_features": "INVALID_REFERENCE: included only as a diagnostic reference because current-bar close-derived information cannot justify execution at that same close unless independently observable before the close.",
            "same_close_lagged_features": "Uses the prior bar's EMA, relative volume, IV and OI conditions before entering at the current close.",
            "cost_bps_round_trip": base_cost_bps,
            "contract_metadata_required": True,
            "bid_ask_quotes_available": False,
        },
        "data_quality": {
            "option_bar_rows": total,
            "contract_identity_coverage": identity / total if total else None,
            "required_columns_present": True,
            "bid_ask_available": False,
            "lot_size_history_available": False,
        },
        "families": names,
        "scenarios": results,
        "gate_metrics": {
            "primary_next_open_pf": primary["profit_factor"],
            "primary_next_open_return_pct": primary["return_pct"],
            "lagged_same_close_pf": lagged["profit_factor"],
            "next_close_pf": next_close["profit_factor"],
            "two_bar_open_pf": two_bar["profit_factor"],
            "invalid_reference_pf": invalid_ref["profit_factor"],
        },
        "gate_reasons": sorted(set(reasons)),
        "next_gate": not reasons,
        "promotion_status": "RESEARCH_ONLY_NO_PAPER_TRADING" if reasons else "RESEARCH_PASS_BUT_EXECUTION_METADATA_STILL_REQUIRED",
        "elapsed_seconds": round(time.time() - start, 2),
    }
    Path(a.out).write_text(json.dumps(result, indent=2))
    print(json.dumps({
        "families": len(names),
        "primary_next_open_pf": primary["profit_factor"],
        "lagged_same_close_pf": lagged["profit_factor"],
        "next_close_pf": next_close["profit_factor"],
        "two_bar_open_pf": two_bar["profit_factor"],
        "invalid_reference_pf": invalid_ref["profit_factor"],
        "gate_reasons": sorted(set(reasons)),
        "next_gate": result["next_gate"],
        "out": a.out,
        "elapsed_seconds": result["elapsed_seconds"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
