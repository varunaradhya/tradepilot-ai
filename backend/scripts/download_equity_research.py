from __future__ import annotations
import argparse,csv,os,sys
from datetime import date
from pathlib import Path
BACKEND=Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:sys.path.insert(0,str(BACKEND))
from app.brokers.dhan import DhanClient
from app.services.fno_research_pipeline import chunk_date_range
from app.services.research_data_cache import ResearchDataCache

def normalize(payload):
    data=payload.get('data',payload) if isinstance(payload,dict) else {}
    keys=('timestamp','open','high','low','close','volume'); n=max((len(data.get(k,[])) for k in keys if isinstance(data.get(k,[]),list)),default=0); rows=[]
    for i in range(n):
        if not all(i<len(data.get(k,[])) for k in ('timestamp','open','high','low','close')): continue
        rows.append({'timestamp':data['timestamp'][i],'open':data['open'][i],'high':data['high'][i],'low':data['low'][i],'close':data['close'][i],'volume':data.get('volume',[0]*n)[i]})
    return rows

def _pick(row,*names):
    for name in names:
        value=row.get(name)
        if value is not None and str(value).strip(): return str(value).strip()
    return ''

def load_symbols(path,master):
    wanted=[x.strip().upper() for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip() and not x.strip().startswith('#')]
    with Path(master).open(newline='',encoding='utf-8-sig') as f: records=list(csv.DictReader(f))
    # Dhan's detailed master is not guaranteed to use the same symbolic column
    # names across revisions. Use the actual segment/exchange markers, but make
    # the equity test tolerant of equivalent values such as EQ/EQUITY.
    by={}
    for r in records:
        exch=_pick(r,'EXCH_ID','SEM_EXM_EXCH_ID').upper()
        seg=_pick(r,'SEGMENT','SEM_SEGMENT').upper()
        if exch!='NSE' or seg!='E': continue
        instr=_pick(r,'INSTRUMENT','SEM_INSTRUMENT_NAME','SEM_EXCH_INSTRUMENT_TYPE').upper()
        # For NSE cash equity, the segment marker E is authoritative enough;
        # exclude known derivatives/funds where an instrument marker exists.
        if instr and any(x in instr for x in ('FUT','OPT','INDEX','WARRANT')): continue
        sid=_pick(r,'SECURITY_ID','SEM_SMST_SECURITY_ID')
        if not sid: continue
        candidates=[_pick(r,'SYMBOL_NAME'),_pick(r,'SEM_TRADING_SYMBOL'),_pick(r,'TRADING_SYMBOL'),_pick(r,'SYMBOL')]
        for raw in candidates:
            sym=raw.upper()
            if sym in wanted:
                by[sym]=sid
                break
    missing=[s for s in wanted if s not in by]
    if missing:
        raise SystemExit(f'Missing NSE equity symbols in Dhan master: {missing}. Parsed {len(records):,} rows; matched {len(by)} requested symbols.')
    return [(s,by[s]) for s in wanted]

def main():
    p=argparse.ArgumentParser(description='Persist five-year NSE equity 5-minute research data for repeated strategy tests.')
    p.add_argument('--master',default='data/reference/dhan_scrip_master_detailed.csv');p.add_argument('--symbols-file',default='data/reference/equity_discovery_universe.txt');p.add_argument('--from-date',required=True);p.add_argument('--to-date',required=True);p.add_argument('--interval',default='5',choices=['1','5','15','25','60']);p.add_argument('--db',default='data/research/market_data.sqlite');a=p.parse_args()
    cid=os.environ.get('DHAN_CLIENT_ID'); token=os.environ.get('DHAN_ACCESS_TOKEN')
    if not cid or not token: raise SystemExit('Set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN before downloading equity research data.')
    start=date.fromisoformat(a.from_date); end=date.fromisoformat(a.to_date)
    symbols=load_symbols(a.symbols_file,a.master); windows=chunk_date_range(start,end,90); dataset=f'equity_nse_discovery_{a.interval}m'; client=DhanClient(cid,token)
    with ResearchDataCache(a.db) as cache:
        cache.dataset(dataset,'Dhan',a.interval,a.from_date,a.to_date,{'exchange':'NSE_EQ','instrument':'EQUITY','symbols':[s for s,_ in symbols],'universe_type':'liquid discovery universe; survivorship-biased until historical membership is added','fields':['OHLC','VOLUME']})
        total=len(symbols)*len(windows); done=0; print(f'Dataset: {dataset} | symbols={len(symbols)} | windows={len(windows)} | requests={total}')
        for symbol,sid in symbols:
            for w in windows:
                key=f'{symbol}:{w.start}:{w.end}'; done+=1
                if cache.done(dataset,key): print(f'[{done}/{total}] cached {symbol} {w.start}->{w.end}'); continue
                print(f'[{done}/{total}] {symbol} ({sid}) {w.start}->{w.end}')
                rows=normalize(client.historical_intraday(sid,'NSE_EQ','EQUITY',a.interval,w.start.isoformat(),w.end.isoformat(),oi=False,expiry_code=0)); cache.put_equity(dataset,symbol,rows); cache.mark_done(dataset,key); print(f'  bars={len(rows)} equity_cache_rows={cache.equity_counts(dataset)}')
        print('EQUITY DOWNLOAD COMPLETE'); print({'equity_rows':cache.equity_counts(dataset),'base_counts':cache.counts()})
if __name__=='__main__': main()
