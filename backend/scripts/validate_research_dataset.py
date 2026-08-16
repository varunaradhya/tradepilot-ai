from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter


def main():
    p = argparse.ArgumentParser(description='Validate the complete NIFTY option research dataset before the next strategy gate.')
    p.add_argument('--db', default='data/research/market_data.sqlite')
    p.add_argument('--dataset-id', default='nifty_options_contract_v2_week_5m_atm10')
    p.add_argument('--from-date', default='2021-08-16')
    p.add_argument('--to-date', default='2026-08-16')
    a = p.parse_args()

    db = sqlite3.connect(a.db)
    try:
        dataset = db.execute(
            'SELECT dataset_id,source,interval,from_date,to_date,metadata_json FROM datasets WHERE dataset_id=?',
            (a.dataset_id,),
        ).fetchone()
        if not dataset:
            raise SystemExit(f'Dataset not found: {a.dataset_id}')

        meta = json.loads(dataset[5])
        expected = ['ATM'] + [f'ATM-{i}' for i in range(1, 11)] + [f'ATM+{i}' for i in range(1, 11)]
        strikes = list(meta.get('strikes') or [])
        errors = []
        warnings = []

        if dataset[3] != a.from_date or dataset[4] != a.to_date:
            errors.append(f'coverage metadata mismatch: {dataset[3]} -> {dataset[4]}')
        if strikes != expected:
            errors.append(f'strike scope mismatch: expected {len(expected)}, got {len(strikes)}')

        windows = db.execute(
            'SELECT COUNT(*) FROM windows WHERE dataset_id=?', (a.dataset_id,)
        ).fetchone()[0]
        expected_windows = sum(1 for _ in range(0, 1))  # replaced below from date chunks
        from datetime import date, timedelta
        start = date.fromisoformat(a.from_date)
        end = date.fromisoformat(a.to_date)
        cur = start
        expected_windows = 0
        while cur < end:
            expected_windows += 1
            cur += timedelta(days=30)
        if windows != expected_windows:
            errors.append(f'window coverage incomplete: {windows}/{expected_windows}')

        option_count = db.execute('SELECT COUNT(*) FROM option_bars').fetchone()[0]
        spot_count = db.execute('SELECT COUNT(*) FROM spot_bars').fetchone()[0]
        missing_identity = db.execute(
            'SELECT COUNT(*) FROM option_bars WHERE expiry IS NULL OR contract_identity IS NULL OR contract_identity=""'
        ).fetchone()[0]
        missing_ohlc = db.execute(
            'SELECT COUNT(*) FROM option_bars WHERE open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL'
        ).fetchone()[0]
        missing_iv_oi = db.execute(
            'SELECT COUNT(*) FROM option_bars WHERE iv IS NULL OR oi IS NULL'
        ).fetchone()[0]
        sides = Counter(r[0] for r in db.execute('SELECT side FROM option_bars').fetchall())
        strike_counts = dict(db.execute(
            'SELECT strike_key, COUNT(*) FROM option_bars GROUP BY strike_key ORDER BY strike_key'
        ).fetchall())
        contract_count = db.execute(
            'SELECT COUNT(DISTINCT contract_identity) FROM option_bars'
        ).fetchone()[0]
        expiry_count = db.execute(
            'SELECT COUNT(DISTINCT expiry) FROM option_bars'
        ).fetchone()[0]
        option_minmax = db.execute(
            'SELECT MIN(timestamp), MAX(timestamp) FROM option_bars'
        ).fetchone()
        spot_minmax = db.execute(
            'SELECT MIN(timestamp), MAX(timestamp) FROM spot_bars'
        ).fetchone()

        if option_count == 0:
            errors.append('no option rows')
        if spot_count == 0:
            errors.append('no NIFTY spot rows')
        if missing_identity:
            errors.append(f'missing expiry/contract identity rows: {missing_identity}')
        if missing_ohlc:
            errors.append(f'missing OHLC rows: {missing_ohlc}')
        if missing_iv_oi:
            warnings.append(f'missing IV/OI rows: {missing_iv_oi}')
        if sides.get('CALL', 0) == 0 or sides.get('PUT', 0) == 0:
            errors.append(f'call/put side coverage incomplete: {dict(sides)}')

        missing_strikes = [s for s in expected if strike_counts.get(s, 0) == 0]
        if missing_strikes:
            errors.append(f'strikes with no rows: {missing_strikes}')

        print(f'RESEARCH DATASET: {a.dataset_id}')
        print(f'coverage={dataset[3]} -> {dataset[4]} interval={dataset[2]}')
        print(f'windows={windows}/{expected_windows}')
        print(f'spot_rows={spot_count} option_rows={option_count}')
        print(f'contracts={contract_count} expiries={expiry_count} sides={dict(sides)}')
        print(f'option_ts={option_minmax} spot_ts={spot_minmax}')
        print(f'missing_identity={missing_identity} missing_ohlc={missing_ohlc} missing_iv_oi={missing_iv_oi}')
        print(f'strike_rows={strike_counts}')

        if warnings:
            print(f'WARNINGS: {warnings}')
        if errors:
            print(f'ERRORS: {errors}')
            print('RESEARCH DATASET GATE: FAIL')
            raise SystemExit(1)

        print('RESEARCH DATASET GATE: PASS')
    finally:
        db.close()


if __name__ == '__main__':
    main()
