from __future__ import annotations

import json
from datetime import datetime, timedelta

from app.services.historical_data_service import MarketBar, validate_dataset


def test_clean_jsonl_matches_market_bar_contract(tmp_path):
    source = tmp_path / "clean.jsonl"
    start = datetime(2026, 1, 2, 9, 15)
    payload = []
    for i in range(75):
        timestamp = start + timedelta(minutes=5 * i)
        payload.append(
            {
                "timestamp": timestamp.isoformat(),
                "open": 100 + i,
                "high": 101 + i,
                "low": 99 + i,
                "close": 100.5 + i,
                "volume": 1000,
            }
        )
    source.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in payload) + "\n",
        encoding="utf-8",
    )

    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    bars = [
        MarketBar(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
        )
        for row in rows
    ]

    diagnostics = validate_dataset(bars)
    assert diagnostics["valid"] is True
    assert diagnostics["bars"] == 75
    assert diagnostics["duplicates"] == 0
    assert diagnostics["non_increasing_timestamps"] == 0
    assert bars[0].timestamp == start
    assert bars[-1].timestamp == start + timedelta(minutes=370)
