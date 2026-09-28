from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from app.services.historical_data_service import MarketBar, validate_dataset
from app.services.intraday_research_service import backtest_intraday_dataset
from app.services.research_store import ResearchStore


def test_clean_jsonl_can_be_imported_as_research_store_dataset(tmp_path):
    source = tmp_path / "clean.jsonl"
    source.write_text(
        "\n".join(
            json.dumps({
                "timestamp": datetime(2026, 1, 2, 9, 15 + i // 12, i % 60),
                "open": 100 + i,
                "high": 101 + i,
                "low": 99 + i,
                "close": 100.5 + i,
                "volume": 1000,
            })
            for i in range(75)
        ) + "\n",
        encoding="utf-8",
    )

    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    bars = [
        MarketBar(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            open=row["open"], high=row["high"], low=row["low"],
            close=row["close"], volume=row["volume"],
        )
        for row in rows
    ]

    diagnostics = validate_dataset(bars)
    assert diagnostics["valid"] is True
    assert diagnostics["bars"] == 75
