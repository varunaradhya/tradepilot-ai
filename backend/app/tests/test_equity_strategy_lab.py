from app.services.equity_strategy_lab import EquityStrategyConfig,backtest_orb_momentum,backtest_vwap_mean_reversion,summarize

def _bars(n=80):
    rows=[]
    base=100.0
    for d in range(3):
        for i in range(n):
            ts=1770000000+d*86400+i*300
            p=base+i*0.05+(5 if i>=3 else 0)
            rows.append({'timestamp':ts,'open':p,'high':p+0.2,'low':p-0.2,'close':p+0.1,'volume':1000+(i*10)})
        base+=1
    return rows

def test_equity_strategy_outputs_are_structured():
    rows=_bars();cfg=EquityStrategyConfig(allow_short=False)
    v1=backtest_orb_momentum(rows,cfg);v2=backtest_vwap_mean_reversion(rows,cfg)
    assert isinstance(v1,list) and isinstance(v2,list)
    s=summarize(v1)
    assert set(('trades','net_pnl','profit_factor','max_drawdown','positive_years')).issubset(s)

def test_equity_strategy_costs_are_recorded():
    rows=_bars();trades=backtest_orb_momentum(rows,EquityStrategyConfig(allow_short=False))
    for t in trades:
        assert t['costs']>=0 and t['slippage']>=0 and 'exit_reason' in t
