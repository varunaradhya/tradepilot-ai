from __future__ import annotations
import argparse,csv,os,sys,re
from datetime import date
from pathlib import Path
BACKEND=Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:sys.path.insert(0,str(BACKEND))
from app.brokers.dhan import DhanClient
from app.services.fno_research_pipeline import chunk_date_range
from app.services.research_data_cache import ResearchDataCache

TICKER_ALIASES={'RELIANCE':['RELIANCE INDUSTRIES'],'HDFCBANK':['HDFC BANK'],'ICICIBANK':['ICICI BANK'],'SBIN':['STATE BANK OF INDIA','STATE BANK INDIA'],'INFY':['INFOSYS'],'TCS':['TATA CONSULTANCY SERVICES'],'ITC':['ITC LIMITED','ITC LTD'],'LT':['LARSEN & TOUBRO','LARSEN AND TOUBRO','LARSEN TOUBRO'],'BHARTIARTL':['BHARTI AIRTEL'],'AXISBANK':['AXIS BANK'],'KOTAKBANK':['KOTAK MAHINDRA BANK'],'M&M':['MAHINDRA & MAHINDRA','MAHINDRA AND MAHINDRA'],'MARUTI':['MARUTI SUZUKI INDIA'],'SUNPHARMA':['SUN PHARMACEUTICAL INDUSTRIES','SUN PHARMACEUTICAL'],'HINDUNILVR':['HINDUSTAN UNILEVER'],'TITAN':['TITAN COMPANY'],'BAJFINANCE':['BAJAJ FINANCE'],'NTPC':['NTPC LIMITED','NTPC LTD'],'ONGC':['OIL AND NATURAL GAS CORPORATION','OIL & NATURAL GAS CORPORATION'],'TATASTEEL':['TATA STEEL']}

def normalize(payload):
    data=payload.get('data',payload) if isinstance(payload,dict) else {}; keys=('timestamp','open','high','low','close','volume'); n=max((len(data.get(k,[])) for k in keys if isinstance(data.get(k,[]),list)),default=0); rows=[]
    for i in range(n):
        if not all(i<len(data.get(k,[])) for k in ('timestamp','open','high','low','close')): continue
        rows.append({'timestamp':data['timestamp'][i],'open':data['open'][i],'high':data['high'][i],'low':data['low'][i],'close':data['close'][i],'volume':data.get('volume',[0]*n)[i]})
    return rows

def clean(value): return re.sub(r'[^A-Z0-9]','',str(value or '').upper())

def load_symbols(path,master):
    # Read universe entries as lines, never characters.
    wanted_raw=[x.strip().upper() for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip() and not x.strip().startswith('#')]
    with Path(master).open(newline='',encoding='utf-8-sig') as f: records=list(csv.DictReader(f))
    eligible=[]
    for r in records:
        exch=(r.get('EXCH_ID') or '').strip().upper(); seg=(r.get('SEGMENT') or '').strip().upper(); instr=(r.get('INSTRUMENT') or '').strip().upper(); typ=(r.get('INSTRUMENT_TYPE') or '').strip().upper()
        if exch=='NSE' and seg=='E' and ('EQUITY' in instr or typ in {'ES','EQ','E','EQUITY'}): eligible.append(r)
    by_symbol={}
    for r in eligible:
        sid=(r.get('SECURITY_ID') or '').strip()
        for f in [r.get('SEM_TRADING_SYMBOL'),r.get('TRADING_SYMBOL'),r.get('SYMBOL_NAME'),r.get('DISPLAY_NAME'),r.get('SEM_CUSTOM_SYMBOL')]:
            if f: by_symbol.setdefault(clean(f),[]).append((r.get('SYMBOL_NAME') or f,sid))
    resolved=[]; unresolved=[]
    for ticker in wanted_raw:
        candidates=[]
        for key in [clean(ticker)]+[clean(a) for a in TICKER_ALIASES.get(ticker,[])]: candidates.extend(by_symbol.get(key,[]))
        if not candidates:
            aliases=TICKER_ALIASES.get(ticker,[ticker])
            for r in eligible:
                name=clean(r.get('SYMBOL_NAME'))
                if any(clean(alias) and clean(alias) in name for alias in aliases): candidates.append((r.get('SYMBOL_NAME') or '',(r.get('SECURITY_ID') or '').strip()))
        candidates=list(dict.fromkeys(x for x in candidates if x[1]))
        if candidates: resolved.append((ticker,candidates[0][1]))
        else: unresolved.append(ticker)
    if unresolved: raise SystemExit(f'Could not resolve NSE cash equities: {unresolved}. Resolved={resolved}')
    print(f'Resolved NSE cash equities: {resolved}')
    return resolved

def main():
    p=argparse.ArgumentParser(description='Persist five-year NSE equity 5-minute research data for repeated strategy tests.')
    p.add_argument('--master',default='data/reference/dhan_scrip_master_detailed.csv'); p.add_argument('--symbols-file',default='data/reference/equity_discovery_universe.txt'); p.add_argument('--from-date',required=True); p.add_argument('--to-date',required=True); p.add_argument('--interval',default='5',choices=['1','5','15','25','60']); p.add_argument('--db',default='data/research/market_data.sqlite'); a=p.parse_args()
    cid=os.environ.get('DHAN_CLIENT_ID'); token=os.environ.get('DHAN_ACCESS_TOKEN')
    if not cid or not token: raise SystemExit('Set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN before downloading equity research data.')
    start=date.fromisoformat(a.from_date); end=date.fromisoformat(a.to_date); symbols=load_symbols(a.symbols_file,a.master); windows=chunk_date_range(start,end,90); dataset=f'equity_nse_discovery_{a.interval}m'; client=DhanClient(cid,token)
    with ResearchDataCache(a.db) as cache:
        cache.dataset(dataset,'Dhan',a.interval,a.from_date,a.to_date,{'exchange':'NSE_EQ','instrument':'EQUITY','symbols':[s for s,_ in symbols],'universe_type':'liquid discovery universe; survivorship-biased until historical membership is added','fields':['OHLC','VOLUME']})
        total=len(symbols)*len(windows); done=0; print(f'Dataset: {dataset} | symbols={len(symbols)} | windows={len(windows)} | requests={total}')
        for symbol,sid in symbols:
            for w in windows:
                key=f'{symbol}:{w.start}:{w.end}'; done+=1
                if cache.done(dataset,key): print(f'[{done}/{total}] cached {symbol} {w.start}->{w.end}'); continue
                print(f'[{done}/{total}] {symbol} (securityId={sid}) {w.start}->{w.end}')
                rows=normalize(client.historical_intraday(sid,'NSE_EQ','EQUITY',a.interval,w.start.isoformat(),w.end.isoformat(),oi=False,expiry_code=0)); cache.put_equity(dataset,symbol,rows); cache.mark_done(dataset,key); print(f'  bars={len(rows)} equity_cache_rows={cache.equity_counts(dataset)}')
        print('EQUITY DOWNLOAD COMPLETE'); print({'equity_rows':cache.equity_counts(dataset),'base_counts':cache.counts()})
if __name__=='__main__': main()
