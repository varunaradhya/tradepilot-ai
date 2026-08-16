from __future__ import annotations
from dataclasses import dataclass, asdict
from math import sqrt
from statistics import mean

@dataclass(frozen=True)
class ValidationResult:
    name: str
    train_trades: int
    test_trades: int
    final_trades: int
    train_return: float
    test_return: float
    final_return: float
    train_expectancy: float
    test_expectancy: float
    final_expectancy: float
    profit_factor: float | None
    max_drawdown: float
    win_rate: float
    costs: float
    slippage: float
    eligible: bool
    rejection_reasons: tuple[str, ...]

    def to_dict(self):
        return asdict(self)


def _stats(returns):
    if not returns:
        return 0, 0.0, 0.0, None, 0.0
    wins = [x for x in returns if x > 0]
    losses = [x for x in returns if x < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    pf = gross_win / gross_loss if gross_loss else (None if not gross_win else float('inf'))
    return len(returns), sum(returns) / len(returns), len(wins) / len(returns), pf, sum(returns)


def _drawdown(returns):
    equity = peak = 0.0
    worst = 0.0
    for r in returns:
        equity += r
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
    return abs(worst)


def _signal(rule, row):
    c = float(row['close'])
    ema20 = float(row.get('ema20', c))
    ema50 = float(row.get('ema50', c))
    rsi = float(row.get('rsi', 50))
    relvol = float(row.get('rel_volume', 0))
    body = float(row.get('body_ratio', 0))
    ret1 = float(row.get('ret_1', 0))
    checks = {
        'trend_up': ema20 > ema50,
        'trend_down': ema20 < ema50,
        'rsi_55_70': 55 <= rsi <= 70,
        'rsi_30_45': 30 <= rsi <= 45,
        'relvol_1_5': relvol >= 1.5,
        'relvol_2': relvol >= 2,
        'body_60': body >= .60,
        'positive_1bar': ret1 > 0,
        'negative_1bar': ret1 < 0,
    }
    return all(checks.get(x, False) for x in rule.split('+'))


def _returns(rows, rule, horizon, cost_bps, slippage_bps):
    out = []
    closes = [float(r['close']) for r in rows]
    friction = (cost_bps + slippage_bps) / 10000.0
    for i in range(len(rows) - horizon):
        if _signal(rule, rows[i]):
            direction = -1 if 'trend_down' in rule or 'negative_1bar' in rule or 'rsi_30_45' in rule else 1
            gross = direction * (closes[i + horizon] / closes[i] - 1)
            out.append(gross - friction)
    return out


def validate_rule(rows, rule, horizon=6, train_ratio=.60, validation_ratio=.20, cost_bps=3.0, slippage_bps=2.0, min_trades=50, min_test_expectancy=0.0, max_drawdown=.20):
    rows = sorted(rows, key=lambda r: r['timestamp'])
    n = len(rows)
    a = int(n * train_ratio)
    b = int(n * (train_ratio + validation_ratio))
    train = _returns(rows[:a], rule, horizon, cost_bps, slippage_bps)
    test = _returns(rows[a:b], rule, horizon, cost_bps, slippage_bps)
    final = _returns(rows[b:], rule, horizon, cost_bps, slippage_bps)
    tn, te, _, _, tr = _stats(train)
    vn, ve, _, _, vr = _stats(test)
    fn, fe, fw, pf, fr = _stats(final)
    reasons = []
    if tn < min_trades: reasons.append('insufficient_train_trades')
    if vn < max(20, min_trades // 2): reasons.append('insufficient_validation_trades')
    if fn < max(20, min_trades // 2): reasons.append('insufficient_final_trades')
    if te <= 0: reasons.append('negative_train_expectancy')
    if ve <= 0: reasons.append('negative_validation_expectancy')
    if fe <= min_test_expectancy: reasons.append('negative_final_expectancy')
    dd = _drawdown(final)
    if dd > max_drawdown: reasons.append('excessive_final_drawdown')
    if pf is not None and pf < 1.10: reasons.append('weak_final_profit_factor')
    return ValidationResult(rule, tn, vn, fn, tr, vr, fr, te, ve, fe, pf, dd, fw, (cost_bps/10000)*fn, (slippage_bps/10000)*fn, not reasons, tuple(reasons))
