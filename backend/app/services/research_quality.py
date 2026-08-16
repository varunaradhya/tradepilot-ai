from __future__ import annotations
from datetime import datetime
import sqlite3

def valid_ohlc(row):
    try:
        o,h,l,c=(float(row[k]) for k in ('open','high','low','close'))
        return min(o,h,l,c)>0 and h>=max(o,c) and l<=min(o,c) and h>=l
    except (KeyError,TypeError,ValueError):
        return False

def ts(v): return datetime.fromtimestamp(int(v))

def series_quality(rows):
    seen=set(); invalid=0; duplicates=0; prev=None; gaps=0
    for r in rows:
        t=int(r['timestamp'])
        if t in seen: duplicates+=1
        seen.add(t)
        if not valid_ohlc(r): invalid+=1
        if prev is not None:
            a,b=ts(prev),ts(t); d=(b-a).total_seconds()
            if a.date()==b.date() and 900<d<=28800: gaps+=1
        prev=t
    return {'bars':len(rows),'unique_timestamps':len(seen),'duplicate_timestamps':duplicates,'invalid_ohlc':invalid,'intraday_gaps_over_15m':gaps,'first':ts(rows[0]['timestamp']).isoformat() if rows else None,'last':ts(rows[-1]['timestamp']).isoformat() if rows else None}

def validate_research_db(path='data/research/market_data.sqlite',equity_dataset='equity_nse_discovery_5m',progress=print):
    db=sqlite3.connect(path); db.row_factory=sqlite3.Row
    try:
        progress('QUALITY GATE: starting SQLite checks...')
        spot=[dict(r) for r in db.execute('SELECT timestamp,open,high,low,close,volume FROM spot_bars ORDER BY timestamp')]
        progress(f'QUALITY GATE: spot {len(spot):,} rows loaded')
        opt=[dict(r) for r in db.execute('SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot FROM option_bars')]
        progress(f'QUALITY GATE: options {len(opt):,} rows loaded')
        symbols=[r[0] for r in db.execute('SELECT DISTINCT symbol FROM equity_bars WHERE dataset_id=? ORDER BY symbol',(equity_dataset,))]
        progress(f'QUALITY GATE: equity symbols {len(symbols)} found')
        equity={}
        for i,s in enumerate(symbols,1):
            rows=[dict(r) for r in db.execute('SELECT timestamp,open,high,low,close,volume FROM equity_bars WHERE dataset_id=? AND symbol=? ORDER BY timestamp',(equity_dataset,s))]
            equity[s]=rows
            progress(f'QUALITY GATE: equity {i}/{len(symbols)} {s}: {len(rows):,} rows')
        keys=[(int(r['timestamp']),r['side'],r['strike_key']) for r in opt]
        report={'database':path,'spot':series_quality(spot),'options':{'rows':len(opt),'unique_keys':len(set(keys)),'duplicate_keys':len(keys)-len(set(keys)),'invalid_ohlc':sum(not valid_ohlc(r) for r in opt)},'equity':{'dataset':equity_dataset,'symbols':symbols,'symbol_count':len(symbols),'rows':sum(len(v) for v in equity.values()),'by_symbol':{s:series_quality(v) for s,v in equity.items()}}}
        report['quality_ok']=bool(spot and report['spot']['duplicate_timestamps']==0 and report['spot']['invalid_ohlc']==0 and report['options']['duplicate_keys']==0 and report['options']['invalid_ohlc']==0 and len(symbols)==20 and all(x['bars']>1000 and x['duplicate_timestamps']==0 and x['invalid_ohlc']==0 for x in report['equity']['by_symbol'].values()))
        progress(f"QUALITY GATE: {'PASS' if report['quality_ok'] else 'FAIL'}")
        return report
    finally: db.close()
