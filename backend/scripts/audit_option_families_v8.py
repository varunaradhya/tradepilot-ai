from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="V8 event-level overlap, additive PnL, drawdown and regime audit for option families.")
    p.add_argument('--db', default='data/research/market_data.sqlite')
    p.add_argument('--input', default='data/research/option_family_v6.json')
    p.add_argument('--out', default='data/research/option_family_v8.json')
    p.add_argument('--horizon', type=int, default=6)
    p.add_argument('--cost-bps', type=float, default=5)
    p.add_argument('--slippage-bps', type=float, default=5)
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
        out.append({**r, 'ema20': e20[i], 'ema50': e50[i], 'rel_volume': float(r.get('volume') or 0) / avg if avg else 0.0})
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


def build_signals(rows, conditions, horizon, friction):
    e = enrich(rows); out = []
    for i in range(len(e) - horizon):
        r = e[i]
        if not signal(r, conditions): continue
        entry, exit_ = float(r['close']), float(e[i + horizon]['close'])
        if entry <= 0: continue
        out.append({'timestamp': r['timestamp'], 'return': exit_ / entry - 1.0 - friction,
                    'side': r['side'], 'strike_key': r['strike_key'], 'strike': r['strike']})
    return out


def max_drawdown_additive(values):
    """Drawdown on cumulative fixed-unit PnL, not reinvested account equity."""
    equity = peak = 0.0; worst = 0.0
    for x in values:
        equity += x
        peak = max(peak, equity)
        if peak > 0:
            worst = min(worst, (equity - peak) / peak)
    return worst


def stats(values):
    if not values:
        return {'trades': 0, 'expectancy': 0.0, 'win_rate': 0.0, 'profit_factor': None,
                'return': 0.0, 'max_drawdown': 0.0, 'return_model': 'additive_fixed_unit'}
    wins = [x for x in values if x > 0]; losses = [-x for x in values if x < 0]
    pf = sum(wins) / sum(losses) if losses else (float('inf') if wins else None)
    return {'trades': len(values), 'expectancy': statistics.mean(values), 'win_rate': len(wins) / len(values),
            'profit_factor': pf, 'return': sum(values), 'max_drawdown': max_drawdown_additive(values),
            'return_model': 'additive_fixed_unit'}


def bucket_regime(spot_rows):
    rows = sorted(spot_rows, key=lambda r: r['timestamp'])
    if not rows: return {}
    closes = [float(r['close']) for r in rows]; out = {}; window = 78
    for i, r in enumerate(rows):
        if i < window: out[r['timestamp']] = 'normal'; continue
        base = closes[i-window]; day_ret = closes[i] / base - 1 if base else 0
        sample = closes[max(0, i-window):i]
        rets = [(sample[j] / sample[j-1] - 1) for j in range(1, len(sample)) if sample[j-1]]
        vol = statistics.pstdev(rets) if len(rets) > 1 else 0
        if vol >= 0.004: regime = 'high_vol'
        elif day_ret >= 0.02: regime = 'strong_up'
        elif day_ret <= -0.02: regime = 'strong_down'
        elif day_ret >= 0.005: regime = 'up'
        elif day_ret <= -0.005: regime = 'down'
        else: regime = 'normal'
        out[r['timestamp']] = regime
    return out


def median_dedup(events):
    grouped = defaultdict(list)
    for e in events: grouped[e['timestamp']].append(e['return'])
    return [(ts, statistics.median(vals), len(vals)) for ts, vals in sorted(grouped.items())]


def correlation(left, right):
    if len(left) < 2: return None
    lm, rm = statistics.mean(left), statistics.mean(right)
    den = math.sqrt(sum((x-lm)**2 for x in left) * sum((y-rm)**2 for y in right))
    return sum((x-lm)*(y-rm) for x,y in zip(left,right)) / den if den else 0.0


def main():
    a = parse_args(); started = time.time()
    src = json.loads(Path(a.input).read_text(encoding='utf-8'))
    families = [r for r in src.get('results', []) if r.get('eligible_for_next_research_gate')]
    if not families: raise SystemExit('V8 requires V6 families eligible_for_next_research_gate.')
    print(f'OPTION FAMILY V8: eligible families={len(families)} {[r["family"] for r in families]}', flush=True)

    specs = sorted({(parse_name(n)[0], parse_name(n)[1]) for f in families for n in f.get('matched_candidate_names', [])})
    db = sqlite3.connect(a.db); db.row_factory = sqlite3.Row; groups = {}
    try:
        for i, (side, strike) in enumerate(specs, 1):
            print(f'OPTION FAMILY V8: loading option group {i}/{len(specs)} {side}:{strike}', flush=True)
            groups[(side, strike)] = [dict(r) for r in db.execute(
                'SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot FROM option_bars WHERE side=? AND strike_key=? ORDER BY timestamp', (side, strike))]
            if i % 3 == 0 or i == len(specs): print(f'OPTION FAMILY V8: loaded {i}/{len(specs)} groups elapsed={time.time()-started:.1f}s', flush=True)
        spot_rows = [dict(r) for r in db.execute('SELECT timestamp, close FROM spot_bars ORDER BY timestamp')]
    finally: db.close()

    regime = bucket_regime(spot_rows); friction = (a.cost_bps + a.slippage_bps) / 10000.0
    family_events = {}; family_reports = []
    for i, f in enumerate(families, 1):
        name = f['family']; side, conditions = family_signature(name); events = []
        for candidate in f.get('matched_candidate_names', []):
            cside, strike, cconditions = parse_name(candidate)
            if cside == side and cconditions == conditions:
                events.extend(build_signals(groups.get((cside, strike), []), conditions, a.horizon, friction))
        events.sort(key=lambda x: x['timestamp']); family_events[name] = events
        raw = stats([e['return'] for e in events]); dedup = median_dedup(events); dedup_stats = stats([x[1] for x in dedup])
        family_reports.append({'family': name, 'raw_signals': len(events), 'unique_signal_timestamps': len(dedup),
                               'overlap_rate': 1-len(dedup)/len(events) if events else 0.0, 'raw': raw, 'timestamp_dedup': dedup_stats})
        print(f'OPTION FAMILY V8: {i}/{len(families)} {name} raw={len(events)} unique_ts={len(dedup)} overlap={family_reports[-1]["overlap_rate"]:.2%}', flush=True)

    all_events=[]; event_owners=defaultdict(set)
    for family, events in family_events.items():
        for e in events: all_events.append({**e, 'family': family}); event_owners[e['timestamp']].add(family)
    portfolio = median_dedup(all_events); portfolio_values=[x[1] for x in portfolio]; portfolio_stats=stats(portfolio_values)
    overlap_counts=Counter(len(v) for v in event_owners.values()); multi=sum(v for k,v in overlap_counts.items() if k>1); overlap_rate=multi/len(event_owners) if event_owners else 0.0

    family_corr={}; family_names=list(family_events)
    for i,left in enumerate(family_names):
        for right in family_names[i+1:]:
            lmap={e['timestamp']:e['return'] for e in family_events[left]}; rmap={e['timestamp']:e['return'] for e in family_events[right]}; common=sorted(set(lmap)&set(rmap))
            family_corr[f'{left} | {right}']={'common_timestamps':len(common),'return_correlation':correlation([lmap[t] for t in common],[rmap[t] for t in common])}

    regime_values=defaultdict(list)
    for ts,ret,_ in portfolio: regime_values[regime.get(ts,'unknown')].append(ret)
    regime_report={k:stats(v) for k,v in sorted(regime_values.items())}
    month_values=defaultdict(list)
    for ts,ret,_ in portfolio: month_values[str(ts)[:7]].append(ret)
    month_stats={k:stats(v) for k,v in sorted(month_values.items())}; positive_months=sum(v['expectancy']>0 for v in month_stats.values()); month_rate=positive_months/len(month_stats) if month_stats else 0.0

    loss_streak=win_streak=cur_loss=cur_win=0
    for x in portfolio_values:
        if x<0: cur_loss+=1; cur_win=0
        elif x>0: cur_win+=1; cur_loss=0
        else: cur_loss=cur_win=0
        loss_streak=max(loss_streak,cur_loss); win_streak=max(win_streak,cur_win)
    top_family=sorted(family_reports,key=lambda r:r['timestamp_dedup']['return'],reverse=True)
    gate=bool(portfolio_stats['trades']>=a.min_trades and portfolio_stats['expectancy']>0 and portfolio_stats['profit_factor'] is not None and portfolio_stats['profit_factor']>=1.05 and portfolio_stats['max_drawdown']>-0.50 and month_rate>=0.50)

    result={'version':'v8','methodology':{'horizon_bars':a.horizon,'friction_bps':a.cost_bps+a.slippage_bps,
        'dedup_method':'median return for signals sharing the same timestamp',
        'return_model':'additive fixed-unit PnL; no full-account compounding across overlapping 5-minute events',
        'drawdown_model':'drawdown of cumulative fixed-unit PnL','regime_method':'spot 1-day return plus rolling 5-minute volatility buckets','minimum_trade_reference':a.min_trades},
        'families':family_reports,'portfolio_after_timestamp_dedup':portfolio_stats,
        'portfolio_overlap':{'unique_timestamps':len(event_owners),'multi_family_timestamps':multi,'multi_family_timestamp_rate':overlap_rate,'timestamp_family_count_distribution':dict(sorted(overlap_counts.items()))},
        'family_return_correlation':family_corr,'drawdown':{'max_drawdown':portfolio_stats['max_drawdown'],'worst_loss_streak':loss_streak,'best_win_streak':win_streak},
        'regime_analysis':regime_report,'monthly_concentration':{'months':len(month_stats),'positive_expectancy_months':positive_months,'positive_month_rate':month_rate,'monthly':month_stats},
        'ranking_by_dedup_return':[{'family':r['family'],'return':r['timestamp_dedup']['return'],'expectancy':r['timestamp_dedup']['expectancy'],'drawdown':r['timestamp_dedup']['max_drawdown']} for r in top_family],
        'next_gate':gate,'promotion_status':'RESEARCH_ONLY_NO_PAPER_TRADING',
        'critical_limit':'This audit uses the existing rolling option cache. Historical contract/expiry identity, bid-ask spreads, fills, lot mechanics and live execution remain unvalidated.',
        'elapsed_seconds':round(time.time()-started,2)}
    Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'families':len(families),'portfolio_trades':portfolio_stats['trades'],'portfolio_expectancy':portfolio_stats['expectancy'],'portfolio_profit_factor':portfolio_stats['profit_factor'],'portfolio_return':portfolio_stats['return'],'portfolio_max_drawdown':portfolio_stats['max_drawdown'],'next_gate':gate,'out':a.out,'elapsed_seconds':result['elapsed_seconds']},indent=2),flush=True)


if __name__ == '__main__': main()
