from __future__ import annotations
import argparse, json, sys
from pathlib import Path
BACKEND=Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path: sys.path.insert(0,str(BACKEND))
from app.services.research_data_cache import ResearchDataCache
from app.services.option_research_pipeline import OptionResearchConfig, simulate_option_days, summarize
from app.services.fno_strategy_v1 import FNOORBConfig

def main():
    p=argparse.ArgumentParser(description='Run option strategy research from local Dhan cache; no API download.')
    p.add_argument('--db',default='data/research/market_data.sqlite'); p.add_argument('--capital',type=float,default=100000); p.add_argument('--strikes',default='ATM'); p.add_argument('--out',default='data/research/options_v1_cached.json'); a=p.parse_args()
    with ResearchDataCache(a.db) as cache:
        strikes={x.strip().upper() for x in a.strikes.split(',') if x.strip()}; spot=cache.spot(); options=cache.options(strikes)
        if not spot or not options: raise SystemExit('Research cache is empty. Run scripts/download_research_data.py first.')
        print(f'Using local cache: spot={len(spot)} option_rows={len(options)} strikes={sorted(strikes)}')
        trades=simulate_option_days(spot,options,OptionResearchConfig(capital=a.capital),FNOORBConfig()); metrics=summarize(trades)
        yearly={}
        for t in trades: yearly[t['date'][:4]]=yearly.get(t['date'][:4],0.0)+float(t['pnl'])
        result={'strategy':'NIFTY ATM weekly option V1','status':'RESEARCH_ONLY','data_source':'local Dhan research cache','cache_counts':cache.counts(),'metrics':metrics,'yearly_pnl':yearly,'trades':trades,'promotion_eligible':False}
        Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps({'cache_counts':cache.counts(),'metrics':metrics,'yearly_pnl':yearly,'promotion_eligible':False},indent=2))
if __name__=='__main__': main()
