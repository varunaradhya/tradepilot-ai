from app.services.intraday_strategy_v2 import generate_intraday_v2_signal

def _rows(n=40):
    rows=[]; p=100.0
    for _ in range(n):
        p += .2; rows.append({'open':p-.05,'high':p+.3,'low':p-.2,'close':p,'volume':1000.0})
    rows[-1]['volume']=2500.0; rows[-1]['close'] += 1.0; rows[-1]['high'] += 1.0
    return rows

def test_v2_requires_relative_strength():
    rows=_rows(); s=generate_intraday_v2_signal([r['open'] for r in rows],[r['high'] for r in rows],[r['low'] for r in rows],[r['close'] for r in rows],[r['volume'] for r in rows])
    assert s['action']=='NEUTRAL'

def test_v2_confirmed_confluence_can_buy():
    rows=_rows(); closes=[r['close'] for r in rows]; market=[100.0+i*.05 for i in range(len(rows))]
    s=generate_intraday_v2_signal([r['open'] for r in rows],[r['high'] for r in rows],[r['low'] for r in rows],closes,[r['volume'] for r in rows],market_closes=market,opening_high=100.0)
    assert s['action']=='BUY'
    assert s['target']>s['entry']>s['stop']
