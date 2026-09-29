# TradePilot AI — Portable Historical Data Import

The canonical import path is:

CSV / Parquet / SQLite / PostgreSQL
→ normalized `MarketBar`
→ shared historical quality contract
→ NSE session validation for intraday NSE equity data
→ deterministic dataset fingerprint
→ existing `ResearchStore` JSONL dataset + provenance sidecar.

## Supported inputs

### CSV
Use `import_csv(HistoricalImportRequest(...))`.

Required columns:
- timestamp/datetime/date/time
- open
- high
- low
- close

Optional:
- volume / vol

### Parquet
Use `import_parquet(HistoricalImportRequest(...))`.
The backend uses the `pyarrow` dependency to read Parquet files.

### SQLite
Use `import_sqlite(HistoricalImportRequest(...))`.
Provide a validated table identifier. The table must expose the canonical market columns or supported aliases.

### PostgreSQL
Use `import_postgresql(HistoricalImportRequest(...), connection_url)`.
The table identifier is validated before being interpolated into the read-only SELECT.

## Validation behavior

All formats use the same normalization and generic quality validation:
- timestamp parsing
- chronological ordering
- duplicate detection
- OHLC relationships
- finite positive prices
- non-negative volume

Intraday NSE-equity imports additionally use the existing NSE calendar/session contract:
- regular session 09:15–15:30 IST
- weekends and holidays
- special-session rejection
- missing trading sessions
- interval gaps
- source timezone consistency

Daily imports use the generic contract because a daily bar does not represent a 09:15–15:30 intraday timestamp.

Invalid data is rejected before persistence. No partial dataset is written.

## Provenance

Each successful import records:
- dataset ID
- source
- symbol
- timeframe
- start/end
- row count
- quality status
- creation timestamp
- deterministic SHA-256 content fingerprint
- source version
- import method
- corporate-action adjustment state
- quality diagnostics

The fingerprint is based on normalized bar content plus symbol/timeframe and is deterministic for the same dataset content.

## Security

SQLite/PostgreSQL table identifiers are validated against a strict identifier grammar. PostgreSQL values are read through SQLAlchemy's parameterized execution layer; no user-supplied values are concatenated into predicates. The import service does not execute arbitrary SQL.

The import layer is intentionally a research/data-ingestion capability. It does not enable broker order execution or change the live-trading safety lock.
