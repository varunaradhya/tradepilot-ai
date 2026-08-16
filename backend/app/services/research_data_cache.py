from __future__ import annotations
import json, sqlite3
from pathlib import Path

SCHEMA='''
CREATE TABLE IF NOT EXISTS datasets(dataset_id TEXT PRIMARY KEY, source TEXT, interval TEXT, from_date TEXT, to_date TEXT, metadata_json TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS windows(dataset_id TEXT, window_key TEXT, PRIMARY KEY(dataset_id,window_key));
CREATE TABLE IF NOT EXISTS spot_bars(timestamp INTEGER PRIMARY KEY, open REAL, high REAL, low REAL, close REAL, volume REAL);
CREATE TABLE IF NOT EXISTS option_bars(timestamp INTEGER, side TEXT, strike_key TEXT, strike REAL, open REAL, high REAL, low REAL, close REAL, volume REAL, oi REAL, iv REAL, spot REAL, PRIMARY KEY(timestamp,side,strike_key));
CREATE TABLE IF NOT EXISTS equity_bars(dataset_id TEXT, symbol TEXT, timestamp INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL, PRIMARY KEY(dataset_id,symbol,timestamp));
CREATE INDEX IF NOT EXISTS idx_opt_contract ON option_bars(side,strike_key,timestamp);
CREATE INDEX IF NOT EXISTS idx_equity_symbol_time ON equity_bars(dataset_id,symbol,timestamp);
'''
class ResearchDataCache:
    def __init__(self,path='data/research/market_data.sqlite'):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self.db=sqlite3.connect(self.path); self.db.executescript(SCHEMA); self.db.commit()
    def close(self): self.db.close()
    def dataset(self,dataset_id,source,interval,from_date,to_date,metadata):
        self.db.execute('INSERT OR REPLACE INTO datasets VALUES(?,?,?,?,?,?,CURRENT_TIMESTAMP)',(dataset_id,source,interval,from_date,to_date,json.dumps(metadata,sort_keys=True))); self.db.commit()
    def done(self,dataset_id,key): return self.db.execute('SELECT 1 FROM windows WHERE dataset_id=? AND window_key=?',(dataset_id,key)).fetchone() is not None
    def mark_done(self,dataset_id,key): self.db.execute('INSERT OR REPLACE INTO windows VALUES(?,?)',(dataset_id,key)); self.db.commit()
    def put_spot(self,rows):
        self.db.executemany('INSERT OR REPLACE INTO spot_bars VALUES(?,?,?,?,?,?)',[(int(r['timestamp']),float(r['open']),float(r['high']),float(r['low']),float(r['close']),float(r.get('volume') or 0)) for r in rows]); self.db.commit()
    def put_options(self,rows):
        self.db.executemany('INSERT OR REPLACE INTO option_bars VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',[(int(r['timestamp']),r['side'],str(r.get('strike_key') or r.get('strike')),r.get('strike'),float(r['open']),float(r['high']),float(r['low']),float(r['close']),float(r.get('volume') or 0),r.get('oi'),r.get('iv'),r.get('spot')) for r in rows]); self.db.commit()
    def put_equity(self,dataset_id,symbol,rows):
        self.db.executemany('INSERT OR REPLACE INTO equity_bars VALUES(?,?,?,?,?,?,?,?)',[(dataset_id,symbol,int(r['timestamp']),float(r['open']),float(r['high']),float(r['low']),float(r['close']),float(r.get('volume') or 0)) for r in rows]); self.db.commit()
    def spot(self): return [dict(zip(('timestamp','open','high','low','close','volume'),r)) for r in self.db.execute('SELECT timestamp,open,high,low,close,volume FROM spot_bars ORDER BY timestamp')]
    def options(self,strikes=None):
        if strikes:
            qmarks=','.join('?'*len(strikes)); sql=f'SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot FROM option_bars WHERE strike_key IN ({qmarks}) ORDER BY timestamp,side'; args=tuple(strikes)
        else: sql='SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot FROM option_bars ORDER BY timestamp,side'; args=()
        cols=('timestamp','side','strike_key','strike','open','high','low','close','volume','oi','iv','spot'); return [dict(zip(cols,r)) for r in self.db.execute(sql,args)]
    def option_rows(self,strikes=None): return self.options(strikes)
    def equity(self,dataset_id,symbol=None):
        if symbol:
            rows=self.db.execute('SELECT timestamp,open,high,low,close,volume FROM equity_bars WHERE dataset_id=? AND symbol=? ORDER BY timestamp',(dataset_id,symbol)); cols=('timestamp','open','high','low','close','volume')
        else:
            rows=self.db.execute('SELECT symbol,timestamp,open,high,low,close,volume FROM equity_bars WHERE dataset_id=? ORDER BY symbol,timestamp',(dataset_id,)); cols=('symbol','timestamp','open','high','low','close','volume')
        return [dict(zip(cols,r)) for r in rows]
    def counts(self):
        return {'spot_bars':self.db.execute('SELECT COUNT(*) FROM spot_bars').fetchone()[0],'option_rows':self.db.execute('SELECT COUNT(*) FROM option_bars').fetchone()[0],'equity_rows':self.db.execute('SELECT COUNT(*) FROM equity_bars').fetchone()[0],'windows':self.db.execute('SELECT COUNT(*) FROM windows').fetchone()[0]}
    def __enter__(self): return self
    def __exit__(self,*args): self.close()
