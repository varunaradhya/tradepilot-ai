from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description='Safely prepare the research DB for a fresh rolling-option download.')
    p.add_argument('--db', default='data/research/market_data.sqlite')
    p.add_argument('--backup', action='store_true', default=True)
    a = p.parse_args()

    db_path = Path(a.db)
    if not db_path.exists():
        raise SystemExit(f'Database not found: {db_path}')

    backup = db_path.with_suffix(db_path.suffix + '.' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.bak')
    shutil.copy2(db_path, backup)
    con = sqlite3.connect(db_path)
    try:
        before = con.execute('SELECT COUNT(*) FROM option_bars').fetchone()[0]
        legacy = con.execute('SELECT COUNT(*) FROM option_bars WHERE contract_identity IS NULL OR expiry IS NULL').fetchone()[0]
        print(f'RESEARCH PREP: option_rows_before={before}')
        print(f'RESEARCH PREP: legacy_rows_without_identity={legacy}')
        if legacy:
            con.execute('DELETE FROM option_bars WHERE contract_identity IS NULL OR expiry IS NULL')
        # Old incomplete download checkpoints must not block the corrected downloader.
        deleted_windows = con.execute("DELETE FROM windows WHERE dataset_id LIKE 'nifty_options_contract_v2_%'").rowcount
        con.commit()
        after = con.execute('SELECT COUNT(*) FROM option_bars').fetchone()[0]
        print(f'RESEARCH PREP: option_rows_after={after}')
        print(f'RESEARCH PREP: old_v2_checkpoints_removed={deleted_windows}')
        print(f'RESEARCH PREP: backup={backup}')
        print('RESEARCH PREP: PASS')
    finally:
        con.close()


if __name__ == '__main__':
    main()
