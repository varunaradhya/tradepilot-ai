from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.brokers.dhan import DhanClient
from app.services.option_research_pipeline import normalize_rolling


def main():
    p = argparse.ArgumentParser(description='Run one Dhan rolling-option request and validate the response shape.')
    p.add_argument('--security-id', default='13')
    p.add_argument('--from-date', default=(date.today() - timedelta(days=7)).isoformat())
    p.add_argument('--to-date', default=date.today().isoformat())
    p.add_argument('--interval', default='5', choices=['1', '5', '15', '25', '60'])
    p.add_argument('--expiry-flag', default='WEEK', choices=['WEEK', 'MONTH'])
    p.add_argument('--expiry-code', type=int, default=0)
    p.add_argument('--strike', default='ATM-3')
    p.add_argument('--option-type', default='CALL', choices=['CALL', 'PUT'])
    a = p.parse_args()

    cid = os.environ.get('DHAN_CLIENT_ID')
    token = os.environ.get('DHAN_ACCESS_TOKEN')
    if not cid or not token:
        raise SystemExit('Set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN before running the diagnostic.')

    client = DhanClient(cid, token)
    raw = client.rolling_option(
        a.security_id, a.expiry_flag, a.expiry_code, a.strike, a.option_type,
        a.from_date, a.to_date, a.interval,
    )
    data = raw.get('data', raw) if isinstance(raw, dict) else {}
    print('DHAN DIAGNOSTIC: request OK')
    print(f'DHAN DIAGNOSTIC: top-level keys={list(raw.keys()) if isinstance(raw, dict) else type(raw).__name__}')
    print(f'DHAN DIAGNOSTIC: data keys={list(data.keys()) if isinstance(data, dict) else type(data).__name__}')

    for side in ('ce', 'pe'):
        block = data.get(side) if isinstance(data, dict) else None
        if block is None:
            print(f'DHAN DIAGNOSTIC: {side}=null/missing')
            continue
        if not isinstance(block, dict):
            print(f'DHAN DIAGNOSTIC: {side}=unexpected {type(block).__name__}')
            continue
        print(f'DHAN DIAGNOSTIC: {side} fields={sorted(block.keys())}')
        for key in ('timestamp', 'open', 'high', 'low', 'close', 'volume', 'strike', 'oi', 'iv', 'spot'):
            value = block.get(key)
            print(f'  {key}: type={type(value).__name__} len={len(value) if isinstance(value, list) else "-"}')
        if isinstance(block.get('timestamp'), list) and block['timestamp']:
            print(f'  first_timestamp={block["timestamp"][0]} last_timestamp={block["timestamp"][-1]}')

    rows = normalize_rolling(raw)
    print(f'DHAN DIAGNOSTIC: normalized_rows={len(rows)}')
    if rows:
        print(json.dumps(rows[0], indent=2, default=str))
        print('DHAN DIAGNOSTIC: PASS')
    else:
        print('DHAN DIAGNOSTIC: FAIL - API returned no normalizable OHLC rows')
        raise SystemExit(2)


if __name__ == '__main__':
    main()
