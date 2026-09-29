from datetime import datetime
from pathlib import Path
import sqlite3

import pytest

from app.services.historical_data_import_service import (
    HistoricalImportRequest,
    import_csv,
    import_rows,
    import_sqlite,
)
from app.services.research_store import ResearchStore


def _rows():
    return [
        {"timestamp": "2026-01-05T09:15:00+05:30", "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 10},
        {"timestamp": "2026-01-05T09:20:00+05:30", "open": 100.5, "high": 102, "low": 100, "close": 101.5, "volume": 12},
    ]


def _request(dataset_id="nse/TCS_5m"):
    return HistoricalImportRequest(
        source="test",
        symbol="TCS",
        timeframe="5m",
        dataset_id=dataset_id,
        expected_interval_minutes=5,
    )


def test_import_rows_uses_shared_contract_and_writes_provenance(tmp_path: Path):
    store = ResearchStore(tmp_path)
    provenance = import_rows(_rows(), _request(), store)
    assert provenance.quality_status == "VALID"
    assert len(provenance.content_fingerprint) == 64
    assert store.get_provenance("nse/TCS_5m")["dataset_id"] == "nse/TCS_5m"
    assert len(store.load("nse/TCS_5m")) == 2


def test_import_csv(tmp_path: Path):
    csv_path = tmp_path / "bars.csv"
    csv_path.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2026-01-05T09:15:00+05:30,100,101,99,100.5,10\n"
        "2026-01-05T09:20:00+05:30,100.5,102,100,101.5,12\n",
        encoding="utf-8",
    )
    provenance = import_csv(_request(), ResearchStore(tmp_path / "store"))
    assert provenance.row_count == 2


def test_import_sqlite(tmp_path: Path):
    database = tmp_path / "source.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE bars (timestamp TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)"
        )
        connection.executemany(
            "INSERT INTO bars VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("2026-01-05T09:15:00+05:30", 100, 101, 99, 100.5, 10),
                ("2026-01-05T09:20:00+05:30", 100.5, 102, 100, 101.5, 12),
            ],
        )
        connection.commit()
    request = HistoricalImportRequest(
        source="sqlite",
        symbol="TCS",
        timeframe="5m",
        dataset_id="nse/TCS_sqlite_5m",
        path=str(database),
        table="bars",
        expected_interval_minutes=5,
    )
    provenance = import_sqlite(request, ResearchStore(tmp_path / "store"))
    assert provenance.row_count == 2


def test_import_rejects_invalid_ohlc(tmp_path: Path):
    rows = _rows()
    rows[0]["high"] = 90
    with pytest.raises(ValueError, match="OHLC"):
        import_rows(rows, _request(), ResearchStore(tmp_path / "store"))


def test_import_rejects_unsafe_table_name(tmp_path: Path):
    database = tmp_path / "source.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE bars (timestamp TEXT, open REAL, high REAL, low REAL, close REAL)")
    request = HistoricalImportRequest(
        source="sqlite",
        symbol="TCS",
        timeframe="5m",
        dataset_id="nse/TCS_sqlite_5m",
        path=str(database),
        table="bars; DROP TABLE bars",
        expected_interval_minutes=5,
    )
    with pytest.raises(ValueError, match="Invalid table identifier"):
        import_sqlite(request, ResearchStore(tmp_path / "store"))
