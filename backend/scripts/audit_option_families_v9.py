from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
import time
from collections import defaultdict
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="V9 capital-aware portfolio simulation for option families.")
    p.add_argument('--db', default='data/research/market_data.sqlite')
    p.add_argument('--input', default='data/research/option_family_v6.json')
    p.add_argument('--out', default='data/research/option_family_v9.json')
    p.add_argument('--horizon', type=int, default=6)
    p.add_argument('--cost-bps', type=float, default=5)
    p.add_argument('--slippage-bps', type=float, default=5)
    p.add_argument('--initial-capital', type=float, default=100000.0)
    p.add_argument('--allocation-pct', type=float, default=0.02)
    p.add_argument('--max-positions', type=int, default=5)
    p.add_argument('--min-trades', type=int, default=100)
    return p.parse_args()


def parse_name(name):
    parts = name.split(':')
    side = parts[0]
    strike = parts[1] if len(parts) > 1 else ''
    conditions = tuple(sorted(c for c in (parts[2].split('+') if len(parts) > 2 else []) if c))
    return side, strike, conditions


def family_signature(name):
    parts = name.split(':')
    side = parts[0]
    raw = parts[2].split('+') if len(parts) >= 3 else (parts[1].split('+') if len(parts) == 2 else [])
    return side, tuple(sorted(c for c in raw if c and c != 'base'))


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
        prior = rows[start:i]
        avg = sum(float(x.get('volume') or 0) for x in prior) / max(len(prior), 1)
        out.append({**r, 'ema20': e20[i], 'ema50': e50[i],
                    'rel_volume': float(r.get('volume') or 0) / avg if avg else 0.0})
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


def build_signals(rows, family, conditions, horizon, friction, family_rank):
    e = enrich(rows); out = []
    for i in range(len(e) - horizon):
        r = e[i]
        if not signal(r, conditions):
            continue
        entry = float(r['close']); exit_ = float(e[i + horizon]['close'])
        if entry <= 0:
            continue
        out.append({
            'timestamp': r['timestamp'],
            'exit_timestamp': e[i + horizon]['timestamp'],
            'return': exit_ / entry - 1.0 - friction,
            'family': family,
            'family_rank': family_rank,
            'side': r['side'],
            'strike_key': r['strike_key'],
            'strike': r['strike'],
        })
    return out


def max_drawdown(equity_curve):
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    worst = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        if peak > 0:
            worst = min(worst, equity / peak - 1.0)
    return worst


def stats(trades, initial_capital):
    if not trades:
        return {
            'trades': 0, 'wins': 0, 'win_rate': 0.0, 'expectancy_return': 0.0,
            'profit_factor': None, 'pnl': 0.0, 'final_capital': initial_capital,
            'total_return_pct': 0.0, 'max_drawdown_pct': 0.0,
            'average_position_pnl': 0.0,
        }
    returns = [t['return'] for t in trades]
    pnls = [t['pnl'] for t in trades]
    wins = [x for x in pnls if x > 0]
    losses = [-x for x in pnls if x < 0]
    equity = []
    value = initial_capital
    for t in sorted(trades, key=lambda x: x['exit_timestamp']):
        value += t['pnl']
        equity.append(value)
    pf = sum(wins) / sum(losses) if losses else (float('inf') if wins else None)
    return {
        'trades': len(trades),
        'wins': len(wins),
        'win_rate': len(wins) / len(trades),
        'expectancy_return': statistics.mean(returns),
        'profit_factor': pf,
        'pnl': sum(pnls),
        'final_capital': initial_capital + sum(pnls),
        'total_return_pct': sum(pnls) / initial_capital,
        'max_drawdown_pct': max_drawdown(equity),
        'average_position_pnl': statistics.mean(pnls),
    }


def select_candidates(candidates, policy):
    if not candidates:
        return []
    if policy == 'all_available':
        return sorted(candidates, key=lambda x: (x['family_rank'], x['family'], x['strike_key']))
    # No future return is used for ranking. Lower family_rank means stronger V7 research ranking.
    best = sorted(candidates, key=lambda x: (x['family_rank'], x['family'], x['strike_key']))[0]
    return [best]


def simulate(events, initial_capital, allocation_pct, max_positions, policy):
    by_entry = defaultdict(list)
    for e in events:
        by_entry[e['timestamp']].append(e)
    timestamps = sorted(by_entry)
    active = []
    capital = initial_capital
    executed = []
    skipped = 0
    max_active = 0
    equity_curve = []
    active_by_family = defaultdict(int)
    family_pnl = defaultdict(float)

    for ts in timestamps:
        still_active = []
        for pos in active:
            if pos['exit_timestamp'] <= ts:
                capital += pos['pnl']
                executed.append(pos)
                family_pnl[pos['family']] += pos['pnl']
            else:
                still_active.append(pos)
        active = still_active

        available_slots = max_positions - len(active)
        candidates = select_candidates(by_entry[ts], policy)
        if policy == 'one_per_family':
            unique = {}
            for c in candidates:
                unique.setdefault(c['family'], c)
            candidates = list(unique.values())

        if available_slots <= 0:
            skipped += len(candidates)
        else:
            for c in candidates:
                if len(active) >= max_positions:
                    skipped += 1
                    continue
                # Position value is fixed as a percentage of equity at entry. No leverage is used.
                position_value = capital * allocation_pct
                if position_value <= 0:
                    skipped += 1
                    continue
                pnl = position_value * c['return']
                pos = {**c, 'entry_capital': capital, 'position_value': position_value, 'pnl': pnl}
                active.append(pos)
                active_by_family[c['family']] += 1
                max_active = max(max_active, len(active))
        equity_curve.append(capital + sum(p['pnl'] for p in active))

    # Mark remaining positions to their historical exit values.
    for pos in sorted(active, key=lambda x: x['exit_timestamp']):
        capital += pos['pnl']
        executed.append(pos)
        family_pnl[pos['family']] += pos['pnl']
        equity_curve.append(capital)

    report = stats(executed, initial_capital)
    report.update({
        'policy': policy,
        'allocation_pct': allocation_pct,
        'max_positions': max_positions,
        'max_simultaneous_positions': max_active,
        'skipped_signals': skipped,
        'capital_utilization_limit_pct': allocation_pct * max_positions,
        'family_pnl': dict(sorted(family_pnl.items(), key=lambda x: x[1], reverse=True)),
    })
    return report, executed


def grid(events, initial_capital, policies):
    out = []
    for policy in policies:
        for allocation in (0.01, 0.02, 0.05):
            for max_pos in (1, 3, 5, 10):
                report, _ = simulate(events, initial_capital, allocation, max_pos, policy)
                out.append(report)
    return out


def gate(best, min_trades):
    return bool(
        best['trades'] >= min_trades and
        best['total_return_pct'] > 0 and
        best['profit_factor'] is not None and best['profit_factor'] >= 1.10 and
        best['max_drawdown_pct'] > -0.30 and
        best['skipped_signals'] < best['trades'] * 2
    )


def main():
    a = parse_args(); started = time.time()
    src = json.loads(Path(a.input).read_text(encoding='utf-8'))
    families = [r for r in src.get('results', []) if r.get('eligible_for_next_research_gate')]
    if not families:
        raise SystemExit('V9 requires V6 families eligible_for_next_research_gate.')

    # Preserve V7 research ranking when deciding which family wins a same-timestamp conflict.
    v7_scores = {}
    v7_path = Path(a.input).with_name('option_family_v7.json')
    if v7_path.exists():
        try:
            v7 = json.loads(v7_path.read_text(encoding='utf-8'))
            for i, row in enumerate(v7.get('results', [])):
                if row.get('family'):
                    v7_scores[row['family']] = i
        except Exception:
            pass
    ranked_names = sorted([f['family'] for f in families], key=lambda n: v7_scores.get(n, 999))
    family_rank = {name: i for i, name in enumerate(ranked_names)}
    print(f'OPTION FAMILY V9: eligible families={len(families)} {ranked_names}', flush=True)

    specs = sorted({(parse_name(n)[0], parse_name(n)[1]) for f in families for n in f.get('matched_candidate_names', [])})
    db = sqlite3.connect(a.db); db.row_factory = sqlite3.Row; groups = {}
    try:
        for i, (side, strike) in enumerate(specs, 1):
            print(f'OPTION FAMILY V9: loading option group {i}/{len(specs)} {side}:{strike}', flush=True)
            groups[(side, strike)] = [dict(r) for r in db.execute(
                'SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot '
                'FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp', (side, strike))]
            if i % 3 == 0 or i == len(specs):
                print(f'OPTION FAMILY V9: loaded {i}/{len(specs)} groups elapsed={time.time()-started:.1f}s', flush=True)
    finally:
        db.close()

    friction = (a.cost_bps + a.slippage_bps) / 10000.0
    events = []
    family_counts = defaultdict(int)
    for f in families:
        name = f['family']; side, conditions = family_signature(name)
        for candidate in f.get('matched_candidate_names', []):
            cside, strike, cconditions = parse_name(candidate)
            if cside == side and cconditions == conditions:
                built = build_signals(groups.get((cside, strike), []), name, conditions, a.horizon, friction, family_rank[name])
                events.extend(built); family_counts[name] += len(built)
    events.sort(key=lambda x: (x['timestamp'], x['family_rank'], x['strike_key']))
    print(f'OPTION FAMILY V9: raw_events={len(events)}', flush=True)

    policies = ['all_available', 'one_per_family', 'top_family_per_timestamp']
    # top_family_per_timestamp and one_per_family differ only when multiple families are active at the same time;
    # both deliberately avoid using future returns for selection.
    reports = grid(events, a.initial_capital, policies)
    for r in reports:
        print(
            f"OPTION FAMILY V9: policy={r['policy']} alloc={r['allocation_pct']:.0%} maxpos={r['max_positions']} "
            f"trades={r['trades']} final={r['final_capital']:.2f} return={r['total_return_pct']:.4%} "
            f"PF={r['profit_factor']} DD={r['max_drawdown_pct']:.2%} skipped={r['skipped_signals']}", flush=True)
        )

    # The default production candidate is deliberately conservative: 2% per trade, five positions,
    # and one family winner per timestamp. This is a research configuration, not an execution instruction.
    default = next(r for r in reports if r['policy'] == 'top_family_per_timestamp' and r['allocation_pct'] == a.allocation_pct and r['max_positions'] == a.max_positions)
    best = max((r for r in reports if r['trades'] >= a.min_trades), key=lambda r: r['total_return_pct'], default=default)
    next_gate = gate(default, a.min_trades)

    result = {
        'version': 'v9',
        'methodology': {
            'horizon_bars': a.horizon,
            'friction_bps': a.cost_bps + a.slippage_bps,
            'initial_capital': a.initial_capital,
            'position_allocation_pct': a.allocation_pct,
            'max_simultaneous_positions': a.max_positions,
            'position_sizing': 'percentage of equity at entry; no leverage; PnL realized at historical exit timestamp',
            'overlap_policy_default': 'top_family_per_timestamp',
            'selection_rule': 'V7 research rank only; future realized return is never used to select a trade',
            'return_model': 'capital-aware realized PnL; no unlimited compounding of overlapping signals',
            'gate_thresholds': {'min_trades': a.min_trades, 'profit_factor': 1.10, 'max_drawdown': -0.30, 'total_return_positive': True},
        },
        'eligible_families': ranked_names,
        'raw_events': len(events),
        'family_event_counts': dict(sorted(family_counts.items())),
        'default_simulation': default,
        'best_grid_result_by_total_return': best,
        'grid_results': reports,
        'next_gate': next_gate,
        'promotion_status': 'RESEARCH_ONLY_NO_PAPER_TRADING',
        'critical_limits': [
            'Historical contract/expiry identity remains unvalidated.',
            'Bid-ask spreads, fills, lot size and liquidity are not modeled beyond the configured friction.',
            'Position allocation is a research capital model, not broker order sizing.',
            'The existing option cache may contain synthetic/rolling contract continuity; live tradability must be validated separately.',
        ],
        'elapsed_seconds': round(time.time() - started, 2),
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({
        'families': len(families),
        'raw_events': len(events),
        'default_trades': default['trades'],
        'default_final_capital': default['final_capital'],
        'default_return_pct': default['total_return_pct'],
        'default_profit_factor': default['profit_factor'],
        'default_max_drawdown_pct': default['max_drawdown_pct'],
        'next_gate': next_gate,
        'out': a.out,
        'elapsed_seconds': result['elapsed_seconds'],
    }, indent=2), flush=True)


if __name__ == '__main__':
    main()
