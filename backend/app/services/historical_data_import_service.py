from __future__ import annotations

from dataclasses import dataclass
import csv
from datetime import date, datetime
import json
import re
import sqlite3
from pathlib import Path
from typing import Iterable

from app.services.dataset_provenance import DatasetProvenance, fingerprint_market_bars
from app.services.historical_data_service import (
    MarketBar,
    normalize_bars,
    validate_dataset,
    validate_nse_equity_dataset,
)
from app.services.research_store import ResearchStore, research_store


_COLUMN_ALIASES = {
    "timestamp": ("timestamp", "datetime", "date", "time"),
    "open": ("open",),
    "high": ("high",),
    "low": ("low",),
    "close": ("close",),
    "volume": ("volume", "vol"),
}
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class HistoricalImportRequest:
    source: str
    symbol: str
    timeframe: str
    dataset_id: str
    path: str | None = None
    table: str | None = None
    expected_interval_minutes: int | None = None
    nse_equity: bool = True
    source_version: str | None = None
    corporate_action_adjusted: bool | None = None


def _find_column(columns: Iterable[str], aliases: tuple[str, ...], required: bool = True) -> str | None:
    normalized = {str(column).strip().lower(): str(column) for column in columns}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    if required:
        raise ValueError(f"Missing required market-data column; expected one of: {', '.join(aliases)}")
    return None


def _rows_from_columns(rows: Iterable[dict]) -> list[dict]:
    rows = list(rows)
    if not rows:
        return []
    columns = list(rows[0].keys())
    mapping = {
        key: _find_column(columns, aliases, required=key != "volume")
        for key, aliases in _COLUMN_ALIASES.items()
    }
    normalized = []
    for row in rows:
        item = {
            "timestamp": row[mapping["timestamp"]],
            "open": row[mapping["open"]],
            "high": row[mapping["high"]],
            "low": row[mapping["low"]],
            "close": row[mapping["close"]],
        }
        if mapping["volume"] is not None:
            item["volume"] = row[mapping["volume"]]
        normalized.append(item)
    return normalized


def _validated_table_name(table: str) -> str:
    parts = table.split(".")
    if not parts or len(parts) > 2 or not all(_IDENTIFIER.fullmatch(part) for part in parts):
        raise ValueError("Invalid table identifier")
    return ".".join(f'"{part}"' for part in parts)


def _read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_jsonl(path: Path) -> list[dict]:
    """Read JSON objects line-by-line without silently dropping bad records."""
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL record on line {line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"JSONL record on line {line_number} must be an object")
            rows.append(row)
    return rows


def _read_parquet(path: Path) -> list[dict]:
    try:
        import pyarrow.parquet as parquet
    except ImportError as exc:
        raise RuntimeError("Parquet import requires the pyarrow dependency") from exc
    table = parquet.read_table(path)
    return table.to_pylist()


def _read_sqlite(path: Path, table: str) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(path)
    quoted = _validated_table_name(table)
    source_uri = f"{path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(source_uri, uri=True) as connection:
        cursor = connection.execute(f"SELECT * FROM {quoted}")
        columns = [description[0] for description in cursor.description or ()]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _read_postgresql(url: str, table: str) -> list[dict]:
    if not url:
        raise ValueError("PostgreSQL connection URL is required")
    try:
        from sqlalchemy import create_engine, text
    except ImportError as exc:
        raise RuntimeError("SQLAlchemy is required for PostgreSQL import") from exc
    quoted = _validated_table_name(table)
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            result = connection.execute(text(f"SELECT * FROM {quoted}"))
            return [dict(row._mapping) for row in result]
    finally:
        engine.dispose()


def _is_daily(timeframe: str) -> bool:
    return timeframe.strip().lower() in {"1d", "day", "daily"}


def _validate_import(
    bars: list[MarketBar],
    request: HistoricalImportRequest,
) -> dict:
    generic = validate_dataset(bars, request.expected_interval_minutes)
    if not generic["valid"]:
        raise ValueError(f"Historical dataset failed quality validation: {generic}")

    if request.nse_equity and not _is_daily(request.timeframe):
        diagnostics = validate_nse_equity_dataset(
            bars,
            expected_interval_minutes=request.expected_interval_minutes,
        )
        if not diagnostics["valid"]:
            raise ValueError(f"Historical dataset failed NSE session validation: {diagnostics}")
        return diagnostics

    return generic


def import_rows(
    rows: Iterable[dict],
    request: HistoricalImportRequest,
    store: ResearchStore = research_store,
) -> DatasetProvenance:
    bars = normalize_bars(_rows_from_columns(rows))
    diagnostics = _validate_import(bars, request)
    fingerprint = fingerprint_market_bars(
        bars,
        symbol=request.symbol,
        timeframe=request.timeframe,
    )
    provenance = DatasetProvenance.create(
        dataset_id=request.dataset_id,
        source=request.source,
        symbol=request.symbol,
        timeframe=request.timeframe,
        bars=bars,
        quality_status="VALID",
        content_fingerprint=fingerprint,
        source_version=request.source_version,
        import_method=request.source,
        corporate_action_adjusted=request.corporate_action_adjusted,
        quality_diagnostics=diagnostics,
    )
    store.save_with_provenance(request.dataset_id, bars, provenance)
    return provenance


def import_csv(request: HistoricalImportRequest, store: ResearchStore = research_store) -> DatasetProvenance:
    if not request.path:
        raise ValueError("CSV path is required")
    return import_rows(_read_csv(Path(request.path)), request, store)


def import_jsonl(request: HistoricalImportRequest, store: ResearchStore = research_store) -> DatasetProvenance:
    if not request.path:
        raise ValueError("JSONL path is required")
    return import_rows(_read_jsonl(Path(request.path)), request, store)


def import_parquet(request: HistoricalImportRequest, store: ResearchStore = research_store) -> DatasetProvenance:
    if not request.path:
        raise ValueError("Parquet path is required")
    return import_rows(_read_parquet(Path(request.path)), request, store)


def import_sqlite(request: HistoricalImportRequest, store: ResearchStore = research_store) -> DatasetProvenance:
    if not request.path or not request.table:
        raise ValueError("SQLite path and table are required")
    return import_rows(_read_sqlite(Path(request.path), request.table), request, store)


def import_postgresql(
    request: HistoricalImportRequest,
    connection_url: str,
    store: ResearchStore = research_store,
) -> DatasetProvenance:
    if not request.table:
        raise ValueError("PostgreSQL table is required")
    return import_rows(_read_postgresql(connection_url, request.table), request, store)
