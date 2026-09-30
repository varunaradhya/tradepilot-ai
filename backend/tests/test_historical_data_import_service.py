from datetime import datetime
import importlib.util
import json
from pathlib import Path
import sqlite3

import pytest

from app.services.historical_data_import_service import (
    HistoricalImportRequest,
    import_csv,
    import_jsonl,
    import_parquet,
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
    provenance = import_csv(HistoricalImportRequest(**{**_request().__dict__, "path": str(csv_path)}), ResearchStore(tmp_path / "store"))
    assert provenance.row_count == 2


def test_import_jsonl_uses_shared_validation_and_provenance(tmp_path: Path):
    source = tmp_path / "bars.jsonl"
    source.write_text("\n".join(json.dumps(row) for row in _rows()) + "\n", encoding="utf-8")
    store = ResearchStore(tmp_path / "store")
    first = import_jsonl(HistoricalImportRequest(**{**_request().__dict__, "path": str(source)}), store)
    second = import_jsonl(
        HistoricalImportRequest(**{**_request("nse/TCS_5m_repeat").__dict__, "path": str(source)}),
        store,
    )
    assert first.row_count == 2
    assert first.content_fingerprint == second.content_fingerprint
    assert first.quality_diagnostics["calendar"]["market"] == "NSE_EQ"
    assert store.get_provenance("nse/TCS_5m")["import_method"] == "test"
    assert len(store.load("nse/TCS_5m")) == 2


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ('{"timestamp":\n', "Invalid JSONL record on line 1"),
        ('{"timestamp":"2026-01-05T09:15:00+05:30","open":100}\n', "Missing required market-data column"),
        ('{"timestamp":"not-a-time","open":100,"high":101,"low":99,"close":100}\n', "Invalid isoformat string"),
        ('{"timestamp":"2026-01-05T09:15:00+05:30","open":100,"high":90,"low":99,"close":100}\n', "Invalid OHLC"),
        ('{"timestamp":"2026-01-05T09:15:00+05:30","open":100,"high":101,"low":99,"close":100,"volume":-1}\n', "Volume must be finite and non-negative"),
    ],
)
def test_import_jsonl_rejects_malformed_or_invalid_records(tmp_path: Path, content: str, message: str):
    source = tmp_path / "invalid.jsonl"
    source.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        import_jsonl(HistoricalImportRequest(**{**_request().__dict__, "path": str(source)}), ResearchStore(tmp_path / "store"))


def test_import_jsonl_applies_nse_duplicate_timestamp_validation(tmp_path: Path):
    source = tmp_path / "duplicate.jsonl"
    source.write_text("\n".join(json.dumps(row) for row in [_rows()[0], _rows()[0]]) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="quality validation"):
        import_jsonl(HistoricalImportRequest(**{**_request().__dict__, "path": str(source)}), ResearchStore(tmp_path / "store"))


def test_import_parquet_explains_missing_optional_dependency(tmp_path: Path):
    if importlib.util.find_spec("pyarrow") is not None:
        pytest.skip("pyarrow is installed; optional-dependency failure path is unavailable")
    with pytest.raises(RuntimeError, match="pyarrow dependency"):
        import_parquet(
            HistoricalImportRequest(**{**_request().__dict__, "path": str(tmp_path / "bars.parquet")}),
            ResearchStore(tmp_path / "store"),
        )


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


def test_import_sqlite_uses_read_only_connection_and_preserves_source(tmp_path: Path, monkeypatch):
    database = tmp_path / "source.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE bars (timestamp TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)")
        connection.executemany("INSERT INTO bars VALUES (?, ?, ?, ?, ?, ?)", [
            ("2026-01-05T09:15:00+05:30", 100, 101, 99, 100.5, 10),
            ("2026-01-05T09:20:00+05:30", 100.5, 102, 100, 101.5, 12),
        ])
    with sqlite3.connect(database) as connection:
        before_schema = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        before_rows = connection.execute("SELECT * FROM bars ORDER BY timestamp").fetchall()

    import app.services.historical_data_import_service as importer
    original_connect = importer.sqlite3.connect
    calls = []

    def recording_connect(*args, **kwargs):
        calls.append((args, kwargs))
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(importer.sqlite3, "connect", recording_connect)
    request = HistoricalImportRequest(
        source="sqlite", symbol="TCS", timeframe="5m", dataset_id="nse/TCS_sqlite_read_only",
        path=str(database), table="bars", expected_interval_minutes=5,
    )
    provenance = import_sqlite(request, ResearchStore(tmp_path / "store"))
    assert provenance.row_count == 2
    assert calls and calls[0][1]["uri"] is True and "mode=ro" in calls[0][0][0]

    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall() == before_schema
        assert connection.execute("SELECT * FROM bars ORDER BY timestamp").fetchall() == before_rows
    with sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True) as connection:
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("CREATE TABLE forbidden (id INTEGER)")
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("UPDATE bars SET close = 0")


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
