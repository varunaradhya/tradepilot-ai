from __future__ import annotations
import argparse,json
from pathlib import Path
import sys
BACKEND=Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:sys.path.insert(0,str(BACKEND))
from app.services.research_data_cache import ResearchDataCache
from app.services.pattern_discovery import discover_patterns,discover_equity_patterns
from app.services.option_pattern_discovery import discover_option_patterns

def main():
    p=argparse.ArgumentParser(description='Discover repeated, interpretable intraday patterns from the local research cache.')
    p.add_argument('--db',default='data/research/market_data.sqlite');p.add_argument('--mode',choices=['nifty','equity','options'],required=True);p.add_argument('--dataset',default='equity_nse_discovery_5m');p.add_argument('--symbol');p.add_argument('--horizon',type=int,default=6);p.add_argument('--min-occurrences',type=int,default=50);p.add_argument('--strikes',nargs='*');p.add_argument('--out',default='data/research/pattern_candidates.json');a=p.parse_args()
    with ResearchDataCache(a.db) as cache:
        if a.mode=='nifty': rows=cache.spot();results=discover_patterns(rows,a.horizon,a.min_occurrences)
        elif a.mode=='equity':
            if not a.symbol:raise SystemExit('--symbol is required for equity mode')
            rows=cache.equity(a.dataset,a.symbol);results=discover_equity_patterns(rows,a.horizon,a.min_occurrences)
        else:
            rows=cache.options(a.strikes);results=discover_option_patterns(rows,a.horizon,a.min_occurrences)
    payload={'mode':a.mode,'dataset':a.dataset,'symbol':a.symbol,'horizon_bars':a.horizon,'input_rows':len(rows),'candidates':[r.to_dict() for r in results]}
    Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(payload,indent=2),encoding='utf-8')
    print(json.dumps({'input_rows':len(rows),'candidate_count':len(results),'robust_candidates':sum(r.robust for r in results),'top_candidates':[r.to_dict() for r in results[:10]]},indent=2))
if __name__=='__main__':main()
