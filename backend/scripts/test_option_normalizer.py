from app.services.option_research_pipeline import normalize_rolling


def main():
    payload = {
        'data': {
            'ce': {
                'timestamp': [1, 2],
                'open': [100, 101],
                'high': [102, 103],
                'low': [99, 100],
                'close': [101, 102],
                'volume': [1000, 1200],
                'strike': [25000, 25000],
                'oi': [50000, 51000],
                'iv': [12.5, 12.7],
                'spot': [24990, 25010],
            },
            'pe': None,
        }
    }
    rows = normalize_rolling(payload)
    assert len(rows) == 2, rows
    assert rows[0]['side'] == 'ce'
    assert rows[0]['close'] == 101
    assert rows[0]['strike'] == 25000
    assert rows[0]['contract_identity'] is None
    print(f'OPTION NORMALIZER TEST: PASS rows={len(rows)}')


if __name__ == '__main__':
    main()
