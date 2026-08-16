from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.brokers.dhan import DhanClient
from app.services.fno_research_pipeline import chunk_date_range
from app.services.option_research_pipeline import normalize_rolling, normalize_spot
from app.services.research_data_cache import ResearchDataCache

# Research scope for the current option-family work.
# Keep the full ATM +/- 10 range so future family discovery does not require another download.
DEFAULT_STRIKES = ','.join(
    ['ATM']
    + [f'ATM-{i}' for i in range(1, 11)]
    + [f'ATM+{i}' for i in range(1, 11)]
)


def main():
    p = argparse.ArgumentParser(
        description='Download and persist the complete NIFTY weekly option research dataset.'
    )
    p.add_argument('--security-id', default='13')
    p.add_argument('--from-date', required=True)
    p.add_argument('--to-date', required=True)
    p.add_argument('--interval', default='5', choices=['1', '5', '15', '25', '60'])
    p.add_argument('--expiry-flag', default='WEEK', choices=['WEEK', 'MONTH'])
    p.add_argument('--expiry-code', type=int, default=0, help='0=near expiry (normalized by DhanClient)')
    p.add_argument('--strikes', default=DEFAULT_STRIKES)
    p.add_argument('--db', default='data/research/market_data.sqlite')
    a = p.parse_args()

    cid = os.environ.get('DHAN_CLIENT_ID')
    token = os.environ.get('DHAN_ACCESS_TOKEN')
    if not cid or not token:
        raise SystemExit('Set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN before downloading research data.')

    start = date.fromisoformat(a.from_date)
    end = date.fromisoformat(a.to_date)
    if start >= end:
        raise SystemExit('from-date must be earlier than to-date')

    strikes = [x.strip().upper() for x in a.strikes.split(',') if x.strip()]
    expected_strikes = ['ATM'] + [f'ATM-{i}' for i in range(1, 11)] + [f'ATM+{i}' for i in range(1, 11)]
    missing = [x for x in expected_strikes if x not in strikes]
    if missing:
        raise SystemExit(f'Incomplete strike scope. Missing: {missing}')

    # v2 deliberately gets a fresh window/checkpoint namespace so an earlier partial
    # v1 download can never cause the expanded dataset to be skipped.
    dataset_id = f'nifty_options_contract_v2_{a.expiry_flag.lower()}_{a.interval}m_atm10'
    metadata = {
        'security_id': a.security_id,
        'expiry_flag': a.expiry_flag,
        'expiry_code': a.expiry_code,
        'strikes': strikes,
        'strike_count_per_side': len(strikes),
        'interval': a.interval,
        'fields': ['OHLC', 'IV', 'VOLUME', 'OI', 'SPOT', 'EXPIRY', 'CONTRACT_IDENTITY'],
        'source': 'Dhan rolling expired options + Dhan historical intraday',
        'contract_identity_required': True,
        'research_scope': 'NIFTY weekly CE/PE ATM-10..ATM+10 plus NIFTY spot',
    }

    client = DhanClient(cid, token)
    windows = chunk_date_range(start, end, 30)

    with ResearchDataCache(a.db) as cache:
        cache.dataset(dataset_id, 'Dhan', a.interval, a.from_date, a.to_date, metadata)
        total = len(windows)
        print(
            f'Dataset: {dataset_id} | {total} windows | '
            f'{len(strikes)} strikes x 2 sides + NIFTY spot'
        )

        for n, w in enumerate(windows, 1):
            key = f'{w.start}:{w.end}'
            if cache.done(dataset_id, key):
                print(f'[{n}/{total}] cached {w.start} -> {w.end}')
                continue

            print(f'[{n}/{total}] {w.start} -> {w.end}')
            spot = client.historical_intraday(
                a.security_id, 'IDX_I', 'INDEX', a.interval,
                w.start.isoformat(), w.end.isoformat(), oi=False, expiry_code=0
            )
            spot_rows = normalize_spot(spot)
            cache.put_spot(spot_rows)

            rows = []
            for strike in strikes:
                for typ in ('CALL', 'PUT'):
                    raw = client.rolling_option(
                        a.security_id, a.expiry_flag, a.expiry_code, strike, typ,
                        w.start.isoformat(), w.end.isoformat(), a.interval
                    )
                    got = normalize_rolling(raw)
                    for r in got:
                        r['strike_key'] = strike
                    rows.extend(
                        r for r in got
                        if r.get('expiry') and r.get('contract_identity')
                    )

            # Never mark an incomplete API window as done. This is important because a
            # transient Dhan response must be retryable instead of silently becoming a gap.
            if not spot_rows or not rows:
                print(
                    f'  WARNING incomplete window: spot={len(spot_rows)} '
                    f'contract_option_rows={len(rows)}; NOT marking cached'
                )
                continue

            cache.put_options(rows)
            cache.mark_done(dataset_id, key)
            print(
                f'  spot={len(spot_rows)} contract_option_rows={len(rows)} '
                f'cache={cache.counts()}'
            )

        print('DOWNLOAD COMPLETE')
        print(cache.counts())


if __name__ == '__main__':
    main()
