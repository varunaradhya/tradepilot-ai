from __future__ import annotations
import argparse, json, random, sqlite3, statistics, sys, time
from pathlib import Path
BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
from app.services.strategy_validation import _stats, _drawdown


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
        out.append({**r, 'ema20': e20[i], 'ema50': e50[i],
                    'rel_volume': float(r.get('volume') or 0) / avg if avg else 0})
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


def returns(rows, conditions, horizon, cost_bps, slippage_bps):
    friction = (cost_bps + slippage_bps) / 10000
    out = []
    for i in range(len(rows) - horizon):
        if signal(rows[i], conditions):
            entry = float(rows[i]['close']); exit_ = float(rows[i + horizon]['close'])
            if entry > 0:
                out.append(exit_ / entry - 1 - friction)
    return out


def monte_carlo(returns_, trials, seed):
    if not returns_:
        return {'trials': 0, 'median_return': 0, 'p05_return': 0, 'probability_positive': 0}
    rng = random.Random(seed)
    totals = []
    for _ in range(trials):
        totals.append(sum(rng.choice(returns_) for _ in returns_))
    return {
        'trials': trials,
        'median_return': statistics.median(totals),
        'p05_return': sorted(totals)[max(0, int(trials * .05) - 1)],
        'probability_positive': sum(x > 0 for x in totals) / trials,
    }


def evaluate(rows, candidate, horizon, cost_bps, slippage_bps, mc_trials, seed):
    parts = candidate['name'].split(':')
    side, strike, *conditions = parts
    group = [r for r in rows if r['side'] == side and r['strike_key'] == strike]
    group = enrich(group)
    n = len(group)
    a, b = int(n * .60), int(n * .80)
    train, validation, final = group[:a], group[a:b], group[b:]
    tr = returns(train, conditions, horizon, cost_bps, slippage_bps)
    va = returns(validation, conditions, horizon, cost_bps, slippage_bps)
    fi = returns(final, conditions, horizon, cost_bps, slippage_bps)
    tn, te, _, tpf, _ = _stats(tr); vn, ve, _, vpf, _ = _stats(va); fn, fe, fw, fpf, fr = _stats(fi)
    reasons = []
    # Selection is allowed to use train+validation only. Final data is untouched.
    if tn < 50: reasons.append('insufficient_train_trades')
    if vn < 25: reasons.append('insufficient_validation_trades')
    if te <= 0: reasons.append('negative_train_expectancy')
    if ve <= 0: reasons.append('negative_validation_expectancy')
    # Final is a reporting gate, never a selection input.
    if fn < 25: reasons.append('insufficient_final_trades')
    if fe <= 0: reasons.append('negative_final_expectancy')
    if fpf is not None and fpf < 1.10: reasons.append('weak_final_profit_factor')
    dd = _drawdown(fi)
    mc = monte_carlo(fi, mc_trials, seed)
    if mc['probability_positive'] < .55: reasons.append('weak_monte_carlo_positive_probability')
    return {
        'name': candidate['name'], 'side': side, 'strike_key': strike,
        'train_trades': tn, 'validation_trades': vn, 'final_trades': fn,
        'train_expectancy': te, 'validation_expectancy': ve, 'final_expectancy': fe,
        'train_profit_factor': tpf, 'validation_profit_factor': vpf, 'final_profit_factor': fpf,
        'final_win_rate': fw, 'final_return': fr, 'final_drawdown': dd,
        'monte_carlo': mc, 'eligible': not reasons, 'rejection_reasons': reasons,
        'selection_uses_final_data': False,
        'research_limit': 'Rolling option series; exact historical contract/expiry execution is not validated.'
    }


def main():
    p = argparse.ArgumentParser(description='Strict option OOS validation. Candidate selection uses only train+validation; final 20%% is untouched until scoring.')
    p.add_argument('--db', default='data/research/market_data.sqlite')
    p.add_argument('--input', default='data/research/option_pattern_lab_v2.json')
    p.add_argument('--out', default='data/research/option_oos_v3.json')
    p.add_argument('--horizon', type=int, default=6)
    p.add_argument('--cost-bps', type=float, default=5)
    p.add_argument('--slippage-bps', type=float, default=5)
    p.add_argument('--monte-carlo-trials', type=int, default=2000)
    p.add_argument('--seed', type=int, default=42)
    a = p.parse_args(); started = time.time()
    src = json.loads(Path(a.input).read_text(encoding='utf-8'))
    candidates = src.get('top_candidates', [])
    db = sqlite3.connect(a.db)
    groups = {}
    specs = list(db.execute('SELECT side,strike_key,COUNT(*) FROM option_bars GROUP BY side,strike_key HAVING COUNT(*)>=200 ORDER BY side,strike_key'))
    print(f'OPTION OOS V3: loading {len(specs)} groups for {len(candidates)} discovery candidates...', flush=True)
    try:
        for i, (side, strike, n) in enumerate(specs, 1):
            rows = [dict(zip(('timestamp','side','strike_key','strike','open','high','low','close','volume','oi','iv','spot'), r)) for r in db.execute('SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp', (side, strike))]
            groups[(side, strike)] = rows
            if i % 5 == 0 or i == len(specs): print(f'OPTION OOS V3: loaded {i}/{len(specs)} groups', flush=True)
        results = []
        for i, c in enumerate(candidates, 1):
            parts = c['name'].split(':'); key = (parts[0], parts[1])
            r = evaluate(groups.get(key, []), c, a.horizon, a.cost_bps, a.slippage_bps, a.monte_carlo_trials, a.seed + i)
            results.append(r)
            print(f'OPTION OOS V3: {i}/{len(candidates)} {c["name"]} final_expectancy={r["final_expectancy"]:.6f} eligible={r["eligible"]}', flush=True)
    finally:
        db.close()
    # Candidates are sorted only after final scores are known; this is a report, not a training step.
    results.sort(key=lambda x: (x['eligible'], x['final_expectancy']), reverse=True)
    report = {
        'methodology': {'train_ratio': .60, 'validation_ratio': .20, 'final_ratio': .20, 'final_is_untouched_for_selection': True,
                        'cost_bps': a.cost_bps, 'slippage_bps': a.slippage_bps, 'monte_carlo_trials': a.monte_carlo_trials},
        'candidate_count': len(results), 'eligible_count': sum(r['eligible'] for r in results),
        'results': results, 'elapsed_seconds': round(time.time() - started, 2),
        'promotion_status': 'RESEARCH_ONLY_NO_PAPER_TRADING',
        'critical_limit': 'This validates rolling option series only. Exact historical contract/expiry execution must pass a separate contract-level test before paper trading.'
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'candidates': len(results), 'eligible': report['eligible_count'], 'elapsed_seconds': report['elapsed_seconds'], 'out': a.out}, indent=2), flush=True)

if __name__ == '__main__': main()
