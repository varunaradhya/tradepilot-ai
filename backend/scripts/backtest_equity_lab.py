from __future__ import annotations
import argparse,json,sys
from pathlib import Path
BACKEND=Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:sys.path.insert(0,str(BACKEND))
from app.services.research_data_cache import ResearchDataCache
from app.services.equity_strategy_lab import EquityStrategyConfig,backtest_orb_momentum,backtest_vwap_mean_reversion,summarize

def main():
    p=argparse.ArgumentParser(description='Compare equity intraday strategy families using cached data only.')
    p.add_argument('--db',default='data/research/market_data.sqlite');p.add_argument('--dataset',default='equity_nse_discovery_5m');p.add_argument('--out',default='data/research/equity_strategy_lab.json');p.add_argument('--long-only',action='store_true');a=p.parse_args()
    cfg=EquityStrategyConfig(allow_short=not a.long_only);results={}
    with ResearchDataCache(a.db) as cache:
        rows=cache.equity(a.dataset)
    symbols=sorted({r['symbol'] for r in rows})
    print(f'Equity research: {len(symbols)} symbols, {len(rows)} bars; local cache only')
    for symbol in symbols:
        sr=[r for r in rows if r['symbol']==symbol]
        v1=backtest_orb_momentum(sr,cfg);v2=backtest_vwap_mean_reversion(sr,cfg)
        results[symbol]={'ORB_MOMENTUM_V1':summarize(v1),'VWAP_MEAN_REVERSION_V2':summarize(v2)}
        print(f'{symbol}: V1 PF={results[symbol]["ORB_MOMENTUM_V1"]["profit_factor"]} PnL={results[symbol]["ORB_MOMENTUM_V1"]["net_pnl"]:.2f}; V2 PF={results[symbol]["VWAP_MEAN_REVERSION_V2"]["profit_factor"]} PnL={results[symbol]["VWAP_MEAN_REVERSION_V2"]["net_pnl"]:.2f}')
    aggregate={}
    for strategy in ('ORB_MOMENTUM_V1','VWAP_MEAN_REVERSION_V2'):
        trades=[]
        for r in results.values():
            # Aggregate only summary-level P&L is insufficient for PF/DD; rerun from cached data.
            pass
        aggregate[strategy]={'symbols_tested':len(symbols),'note':'Per-symbol results are the primary discovery output; promotion requires pooled portfolio backtest, walk-forward and historical-universe validation.'}
    out={'dataset':a.dataset,'universe':symbols,'methodology':{'costs_bps_round_trip':cfg.round_trip_cost_bps,'slippage_bps':cfg.slippage_bps,'orb_bars':cfg.opening_bars,'strategy_families':['ORB_MOMENTUM_V1','VWAP_MEAN_REVERSION_V2']},'results':results,'aggregate':aggregate,'promotion_eligible':False}
    Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf-8');print(f'Wrote {a.out}')
if __name__=='__main__':main()
