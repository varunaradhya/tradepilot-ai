from __future__ import annotations
import argparse, json, random, statistics, sqlite3, sys, time
from pathlib import Path
BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
from app.services.strategy_validation import _stats, _drawdown


def parse_name(name):
    parts = name.split(':')
    side = parts[0]
    strike = parts[1] if len(parts) > 1 else ''
    conditions = tuple(sorted(c for c in (parts[2].split('+') if len(parts) > 2 else []) if c))
    return side, strike, conditions


def family_signature(name):
    parts = name.split(':')
    side = parts[0]
    if len(parts) >= 3:
        conditions = parts[2].split('+')
    elif len(parts) == 2:
        conditions = parts[1].split('+')
    else:
        conditions = []
    return side, tuple(sorted(c for c in conditions if c and c != 'base'))


def enrich(rows):
    rows = sorted(rows, key=lambda r: r['timestamp'])
    if not rows:
        return []
    closes = [float(r['close']) for r in rows]
    k20, k50 = 2 / 21, 2 / 51
    e20, e50 = [], []
    a = b = closes[0]
    for c in closes:
        a = c * k20 + a * (1 - k20)
        b = c * k50 + b * (1 - k50)
        e20.append(a); e50.append(b)
    out = []
    for i, r in enumerate(rows):
        start = max(0, i - 20)
        avg = sum(float(x.get('volume') or 0) for x in rows[start:i]) / max(i - start, 1)
        out.append({**r, 'ema20': e20[i], 'ema50': e50[i], 'rel_volume': float(r.get('volume') or 0) / avg if avg else 0})
    return out


def signal(row, conditions):
    for c in conditions:
        if c == 'premium_trend' and not row['ema20'] > row['ema50']: return False
        if c == 'premium_weak' and not row['ema20'] < row['ema50']: return False
        if c == 'relvol_1_5' and not row['rel_volume'] >= 1.5: return False
        if c == 'iv_high' and not float(row.get('iv') or 0) > 20: return False
        if c == 'iv_low' and not 0 < float(row.get('iv') or 0) < 15: return False
        if c == 'oi_present' and not float(row.get('oi') or 0) > 0: return False
    return True


def candidate_returns(rows, conditions, horizon, cost_bps, slippage_bps):
    friction = (cost_bps + slippage_bps) / 10000
    enriched = enrich(rows)
    out = []
    for i in range(len(enriched) - horizon):
        if signal(enriched[i], conditions):
            entry = float(enriched[i]['close']); exit_ = float(enriched[i + horizon]['close'])
            if entry > 0:
                out.append((enriched[i]['timestamp'], exit_ / entry - 1 - friction))
    return out


def split_returns(values):
    values = sorted(values, key=lambda x: x[0])
    n = len(values); a, b = int(n * .60), int(n * .80)
    return values[:a], values[a:b], values[b:]


def mc(values, trials, seed):
    if not values:
        return {'trials': 0, 'probability_positive': 0.0, 'p05_total': 0.0, 'median_total': 0.0}
    rng = random.Random(seed)
    totals = [sum(rng.choice(values) for _ in values) for _ in range(trials)]
    totals.sort()
    return {'trials': trials, 'probability_positive': sum(x > 0 for x in totals) / trials, 'p05_total': totals[max(0, int(trials * .05) - 1)], 'median_total': statistics.median(totals)}


def evaluate_family(family, candidates, groups, horizon, cost_bps, slippage_bps, mc_trials, seed):
    side, conditions = family_signature(family)
    variant_rows = []
    all_by_ts = {}
    for c in sorted(candidates, key=lambda x: parse_name(x['name'])[1]):
        cside, strike, cconditions = parse_name(c['name'])
        if cside != side or cconditions != conditions:
            continue
        rr = candidate_returns(groups.get((cside, strike), []), conditions, horizon, cost_bps, slippage_bps)
        tr, va, fi = split_returns(rr)
        tn, te, _, tpf, _ = _stats([x[1] for x in tr])
        vn, ve, _, vpf, _ = _stats([x[1] for x in va])
        fn, fe, fw, fpf, fr = _stats([x[1] for x in fi])
        for ts, val in fi:
            all_by_ts.setdefault(ts, []).append(val)
        variant_rows.append({
            'name': c['name'], 'strike_key': strike, 'v3_eligible': bool(c.get('eligible')),
            'final_trades': fn, 'train_expectancy': te, 'validation_expectancy': ve,
            'final_expectancy': fe, 'final_profit_factor': fpf, 'final_win_rate': fw,
            'final_return': fr, 'final_drawdown': _drawdown([x[1] for x in fi]),
        })

    family_returns = [(ts, statistics.median(vals)) for ts, vals in sorted(all_by_ts.items())]
    tr, va, fi = split_returns(family_returns)
    trv = [x[1] for x in tr]; vav = [x[1] for x in va]; fiv = [x[1] for x in fi]
    tn, te, _, tpf, _ = _stats(trv)
    vn, ve, _, vpf, _ = _stats(vav)
    fn, fe, fw, fpf, fr = _stats(fiv)
    mcres = mc(fiv, mc_trials, seed)

    exp = [r['final_expectancy'] for r in variant_rows if r['final_expectancy'] is not None]
    med = statistics.median(exp) if exp else 0.0
    pos = sum(x > 0 for x in exp) / len(exp) if exp else 0.0
    raw_exp = list(exp)
    trimmed = sorted(exp)
    k = int(len(trimmed) * .10)
    trimmed = trimmed[k:-k] if k else trimmed
    trimmed_mean = statistics.mean(trimmed) if trimmed else 0.0

    reasons = []
    if len(variant_rows) < 3: reasons.append('too_few_strike_variants')
    if pos < .70: reasons.append('weak_positive_variant_rate')
    if med <= 0 or trimmed_mean <= 0: reasons.append('weak_variant_expectancy')
    if fn < 50: reasons.append('insufficient_family_final_trades')
    if fpf is not None and fpf < 1.10: reasons.append('weak_family_final_profit_factor')
    if mcres['probability_positive'] < .60: reasons.append('weak_monte_carlo')

    sorted_exp = sorted(raw_exp)
    return {
        'family': family, 'variants': len(variant_rows),
        'matched_candidate_names': [r['name'] for r in variant_rows],
        'v3_eligible_variants': sum(r['v3_eligible'] for r in variant_rows),
        'strike_keys': sorted({r['strike_key'] for r in variant_rows}, key=str),
        'positive_variant_rate': pos, 'median_variant_final_expectancy': med,
        'trimmed_variant_final_expectancy': trimmed_mean,
        'expectancy_diagnostics': {
            'count': len(raw_exp),
            'positive_count': sum(x > 0 for x in raw_exp),
            'zero_count': sum(x == 0 for x in raw_exp),
            'negative_count': sum(x < 0 for x in raw_exp),
            'min': min(raw_exp) if raw_exp else 0.0,
            'max': max(raw_exp) if raw_exp else 0.0,
            'mean': statistics.mean(raw_exp) if raw_exp else 0.0,
            'median': med,
            'trim_fraction_each_side': 0.10,
            'trim_count_each_side': k,
            'trimmed_source_values': trimmed,
            'sorted_source_values': sorted_exp,
        },
        'family_train_trades': tn, 'family_validation_trades': vn, 'family_final_trades': fn,
        'family_train_expectancy': te, 'family_validation_expectancy': ve,
        'family_final_expectancy': fe, 'family_final_profit_factor': fpf,
        'family_final_win_rate': fw, 'family_final_return': fr,
        'family_final_drawdown': _drawdown(fiv), 'monte_carlo': mcres,
        'eligible_for_contract_gate': bool(variant_rows) and not reasons,
        'rejection_reasons': reasons if variant_rows else ['no_matching_v3_candidates'],
        'variant_results': sorted(variant_rows, key=lambda x: x['final_expectancy'], reverse=True),
        'research_limit': 'Rolling option series only; exact contract, expiry, spread, fill and lot mechanics remain unvalidated.'
    }


def main():
    p = argparse.ArgumentParser(description='V5 strict option family robustness audit before exact-contract validation.')
    p.add_argument('--db', default='data/research/market_data.sqlite')
    p.add_argument('--input', default='data/research/option_family_audit_v4.json')
    p.add_argument('--out', default='data/research/option_family_v5.json')
    p.add_argument('--horizon', type=int, default=6)
    p.add_argument('--cost-bps', type=float, default=5)
    p.add_argument('--slippage-bps', type=float, default=5)
    p.add_argument('--monte-carlo-trials', type=int, default=2000)
    p.add_argument('--seed', type=int, default=42)
    a = p.parse_args(); started = time.time()

    src = json.loads(Path(a.input).read_text(encoding='utf-8'))
    approved = src.get('next_gate_candidates', [])
    approved_families = [f['family'] for f in approved]
    print(f'OPTION FAMILY V5: V4 approved={len(approved_families)} families={approved_families}', flush=True)

    v3_path = Path(a.input).with_name('option_oos_v3.json')
    v3 = json.loads(v3_path.read_text(encoding='utf-8'))
    all_candidates = v3.get('results', [])

    fams = {}
    for family in approved_families:
        sig = family_signature(family)
        fams[family] = [c for c in all_candidates if family_signature(c['name']) == sig]
        print(f'OPTION FAMILY V5: family map {family} -> {len(fams[family])} V3 candidates', flush=True)

    db = sqlite3.connect(a.db); groups = {}
    specs = sorted({(parse_name(c['name'])[0], parse_name(c['name'])[1]) for rows in fams.values() for c in rows})
    print(f'OPTION FAMILY V5: approved_families={len(fams)} matched_variants={sum(len(x) for x in fams.values())} groups={len(specs)}', flush=True)
    try:
        for i, (side, strike) in enumerate(specs, 1):
            print(f'OPTION FAMILY V5: loading group {i}/{len(specs)} {side}:{strike}', flush=True)
            rows = [dict(zip(('timestamp','side','strike_key','strike','open','high','low','close','volume','oi','iv','spot'), r)) for r in db.execute('SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp', (side, strike))]
            groups[(side, strike)] = rows
            if i % 3 == 0 or i == len(specs):
                print(f'OPTION FAMILY V5: loaded {i}/{len(specs)} groups elapsed={time.time()-started:.1f}s', flush=True)
    finally:
        db.close()

    results = []
    for i, (fam, rows) in enumerate(sorted(fams.items()), 1):
        r = evaluate_family(fam, rows, groups, a.horizon, a.cost_bps, a.slippage_bps, a.monte_carlo_trials, a.seed + i)
        results.append(r)
        reason = ','.join(r['rejection_reasons']) if r['rejection_reasons'] else 'NONE'
        print(f'OPTION FAMILY V5: {i}/{len(fams)} {fam} variants={r["variants"]} v3_eligible={r["v3_eligible_variants"]} positive={r["positive_variant_rate"]:.2f} median={r["median_variant_final_expectancy"]:.6f} trimmed={r["trimmed_variant_final_expectancy"]:.6f} family_final={r["family_final_expectancy"]:.6f} PF={r["family_final_profit_factor"]} MC={r["monte_carlo"]["probability_positive"]:.3f} eligible={r["eligible_for_contract_gate"]} reasons={reason}', flush=True)
        for vr in r['variant_results']:
            print(f'OPTION FAMILY V5 DIAG: {vr["name"]} final_trades={vr["final_trades"]} expectancy={vr["final_expectancy"]:.6f} PF={vr["final_profit_factor"]} win_rate={vr["final_win_rate"]:.3f} return={vr["final_return"]:.6f}', flush=True)

    results.sort(key=lambda x: (x['eligible_for_contract_gate'], x['median_variant_final_expectancy']), reverse=True)
    report = {
        'methodology': {'train_ratio': .60, 'validation_ratio': .20, 'final_ratio': .20, 'family_definition': 'Exact V4 family signature (side + all strategy conditions); strike offsets are robustness variants.', 'cost_bps': a.cost_bps, 'slippage_bps': a.slippage_bps, 'monte_carlo_trials': a.monte_carlo_trials, 'final_is_not_used_for_selection': True, 'v3_eligibility_is_diagnostic_only': True},
        'input_families': len(fams), 'contract_gate_count': sum(r['eligible_for_contract_gate'] for r in results), 'results': results,
        'promotion_status': 'RESEARCH_ONLY_NO_PAPER_TRADING', 'critical_limit': 'Rolling option series only. Exact historical contract/expiry, bid-ask spread, fill, lot size and expiry-roll mechanics remain unvalidated.', 'elapsed_seconds': round(time.time() - started, 2)
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'families': len(results), 'contract_gate': report['contract_gate_count'], 'elapsed_seconds': report['elapsed_seconds'], 'out': a.out}, indent=2), flush=True)

if __name__ == '__main__': main()
