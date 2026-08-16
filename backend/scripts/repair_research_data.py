from __future__ import annotations
import argparse,json,sqlite3
from pathlib import Path
import sys
BACKEND=Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path: sys.path.insert(0,str(BACKEND))
from app.services.research_quality import valid_ohlc

def main():
    p=argparse.ArgumentParser(description='Quarantine provider-invalid research bars without fabricating market data.')
    p.add_argument('--db',default='data/research/market_data.sqlite');p.add_argument('--out',default='data/research/repair_report.json');a=p.parse_args()
    db_path=Path(a.db); backup=db_path.with_suffix('.pre_repair.sqlite')
    db=sqlite3.connect(db_path); db.row_factory=sqlite3.Row
    try:
        rows=list(db.execute('SELECT timestamp,open,high,low,close,volume FROM spot_bars ORDER BY timestamp'))
        bad=[dict(r) for r in rows if not valid_ohlc(r)]
        print(f'REPAIR: found {len(bad)} invalid NIFTY spot bars')
        if not bad:
            report={'repaired':False,'removed_spot_bars':0,'backup':None,'invalid_rows':[]}
        else:
            if backup.exists(): backup.unlink()
            backup_db=sqlite3.connect(backup); db.backup(backup_db); backup_db.close()
            db.executemany('DELETE FROM spot_bars WHERE timestamp=?',[(int(r['timestamp']),) for r in bad]); db.commit()
            report={'repaired':True,'removed_spot_bars':len(bad),'backup':str(backup),'invalid_rows':bad}
            print(f'REPAIR: removed {len(bad)} invalid bars; backup={backup}')
        Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
        print(json.dumps({'repaired':report['repaired'],'removed_spot_bars':report['removed_spot_bars'],'backup':report['backup']},indent=2))
    finally: db.close()
if __name__=='__main__': main()
