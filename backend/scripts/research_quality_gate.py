from __future__ import annotations
import argparse,json
from pathlib import Path
import sys
BACKEND=Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path: sys.path.insert(0,str(BACKEND))
from app.services.research_quality import validate_research_db

def main():
    p=argparse.ArgumentParser(description='Validate the persisted F&O and equity research dataset before strategy discovery.')
    p.add_argument('--db',default='data/research/market_data.sqlite');p.add_argument('--equity-dataset',default='equity_nse_discovery_5m');p.add_argument('--out',default='data/research/quality_gate.json');a=p.parse_args()
    report=validate_research_db(a.db,a.equity_dataset)
    Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'quality_ok':report['quality_ok'],'spot':report['spot'],'options':report['options'],'equity_summary':{'symbols':report['equity']['symbol_count'],'rows':report['equity']['rows'],'bad_symbols':[s for s,v in report['equity']['by_symbol'].items() if v['invalid_ohlc'] or v['duplicate_timestamps'] or v['bars']<=1000]}},indent=2))
    if not report['quality_ok']: raise SystemExit(2)
if __name__=='__main__': main()
