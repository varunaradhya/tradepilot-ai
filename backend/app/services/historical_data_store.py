from __future__ import annotations
import json, sqlite3
from pathlib import Path
from typing import Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS datasets (
  dataset_id TEXT PRIMARY KEY, source TEXT NOT NULL, interval TEXT NOT NULL,
  from_date TEXT NOT NULL, to_date TEXT NOT NULL, metadata_json TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS spot_bars (
  timestamp INTEGER PRIMARY KEY, open REAL NOT NULL, high REAL NOT NULL,
  low REAL NOT NULL, close REAL NOT NULL, volume REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS option_bars (
  timestamp INTEGER NOT NULL, side TEXT NOT NULL, strike_key TEXT NOT NULL,
  strike REAL, open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL,
  close REAL NOT NULL, volume REAL DEFAULT 0, oi REAL, iv REAL, spot REAL,
  PRIMARY KEY(timestamp, side, strike_key)
);
CREATE INDEX IF NOT EXISTS idx_option_time ON option_bars(timestamp);
CREATE INDEX IF NOT EXISTS idx_option_contract ON option_bars(side, strike_key, timestamp);
"""

class HistoricalDataStore:
    """Persistent local SQLite cache for Dhan research data. Download once, research many times."""
    def __init__(self, path: str | Path):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.path); self.con.executescript(SCHEMA); self.con.commit()
    def close(self): self.con.close()
    def upsert_spot(self, rows: Iterable[dict]) -> int:
        rows=list(rows); self.con.executemany("INSERT OR REPLACE INTO spot_bars(timestamp,open,high,low,close,volume) VALUES(?,?,?,?,?,?)", [(int(r['timestamp']),float(r['open']),float(r['high']),float(r['low']),float(r['close']),float(r.get('volume') or 0)) for r in rows]); self.con.commit(); return len(rows)
    def upsert_options(self, rows: Iterable[dict]) -> int:
        rows=list(rows); self.con.executemany("INSERT OR REPLACE INTO option_bars(timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", [(int(r['timestamp']),r['side'],str(r.get('strike_key') or r.get('strike')),float(r['strike']) if r.get('strike') is not None else None,float(r['open']),float(r['high']),float(r['low']),float(r['close']),float(r.get('volume') or 0),float(r['oi']) if r.get('oi') is not None else None,float(r['iv']) if r.get('iv') is not None else None,float(r['spot']) if r.get('spot') is not None else None) for r in rows]); self.con.commit(); return len(rows)
    def set_dataset(self, dataset_id: str, source: str, interval: str, from_date: str, to_date: str, metadata: dict):
        self.con.execute("INSERT OR REPLACE INTO datasets(dataset_id,source,interval,from_date,to_date,metadata_json,updated_at) VALUES(?,?,?,?,?,?,CURRENT_TIMESTAMP)",(dataset_id,source,interval,from_date,to_date,json.dumps(metadata,sort_keys=True))); self.con.commit()
    def get_dataset(self, dataset_id: str):
        row=self.con.execute("SELECT dataset_id,source,interval,from_date,to_date,metadata_json,updated_at FROM datasets WHERE dataset_id=?",(dataset_id,)).fetchone()
        if not row: return None
        return {'dataset_id':row[0],'source':row[1],'interval':row[2],'from_date':row[3],'to_date':row[4],'metadata':json.loads(row[5]),'updated_at':row[6]}
    def spot_rows(self): return [dict(timestamp=r[0],open=r[1],high=r[2],low=r[3],close=r[4],volume=r[5]) for r in self.con.execute("SELECT timestamp,open,high,low,close,volume FROM spot_bars ORDER BY timestamp")]
    def option_rows(self, strikes: set[str] | None = None):
        if strikes:
            marks=','.join('?' for _ in strikes); q=f"SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot FROM option_bars WHERE strike_key IN ({marks}) ORDER BY timestamp,side"; args=tuple(strikes)
        else: q="SELECT timestamp,side,strike_key,strike,open,high,low,close,volume,oi,iv,spot FROM option_bars ORDER BY timestamp,side"; args=()
        return [dict(timestamp=r[0],side=r[1],strike_key=r[2],strike=r[3],open=r[4],high=r[5],low=r[6],close=r[7],volume=r[8],oi=r[9],iv=r[10],spot=r[11]) for r in self.con.execute(q,args)]
    def counts(self): return {'spot_bars':self.con.execute('SELECT COUNT(*) FROM spot_bars').fetchone()[0], 'option_rows':self.con.execute('SELECT COUNT(*) FROM option_bars').fetchone()[0], 'datasets':self.con.execute('SELECT COUNT(*) FROM datasets').fetchone()[0]}
    def __enter__(self): return self
    def __exit__(self,*args): self.close()
