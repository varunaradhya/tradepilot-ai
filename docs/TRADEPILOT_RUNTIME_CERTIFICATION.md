# TradePilot AI Runtime Certification

## Scope and environment

Certification was executed on Windows at commit `82b67efd7eb81756da60c68ddcc9a97a89b3b895` using Python 3.12.10 in an isolated `backend/.venv-certification` environment. Docker was unavailable and was not used. Raw market data and the original SQLite database were not modified.

## Executed checks

| Gate | Result | Evidence |
| --- | --- | --- |
| Pinned backend dependencies | PASS | `pip check` completed without broken requirements. |
| Backend regression suite | PASS | 740 passed, 7 warnings. |
| Frontend dependency install and production build | PASS | `npm.cmd ci` completed; Vite production build completed. |
| Fresh SQLite migrations | PASS | Empty database upgraded to head, downgraded to `20260818_0004`, then upgraded to head. |
| Next-bar, paper, reconciliation, and live-lock focused checks | PASS | 12 focused tests passed before the full suite; F&O remains hard-coded paper-only. |
| Real-data importer/provenance regression tests | PASS | CSV deterministic provenance and read-only SQLite import tests passed. |

## Migration repair

The base Alembic revision did not create `paper_trades`, although revision `20260821_0005` altered that table. The base migration now creates the pre-option columns and indexes. Revision `20260928_0009` also no longer requests duplicate SQLite indexes through both column metadata and explicit index creation.

## Real historical data

The local Dhan-derived NSE dataset `equity_nse_discovery_5m` contains 20 equity symbols, 1,825,166 clean rows and 29,804 quarantined rows according to its existing manifest. The original files were read only.

The first isolated TCS exercise used 76 rows for 2021-08-16 from the clean TCS partition. Generic OHLC, volume, duplicate, chronological-order, and ResearchStore persistence checks passed. Its deterministic SHA-256 fingerprint was `40d69c6a5804b5c8e135b3d73a09bcc6f60518fe716070e29fd6a5ac6d222098`; a re-read produced the same fingerprint. Corporate-action state is `UNKNOWN`.

### Data limitation: timestamp interval irregularity

The TCS source is not strictly certifiable as 5-minute bars. 43 of 75 adjacent intervals were not exactly 300 seconds; observed deltas ranged from 239 to 361 seconds. No timestamps were rounded, resampled, repaired, or removed. The session had 76 accepted boundary/count bars (09:15–15:30 Asia/Kolkata), but strict interval validation remains a **DATA LIMITATION**.

## Historical import and provenance

`HistoricalImportRequest`, `DatasetProvenance`, deterministic `fingerprint_market_bars`, and `import_historical_data` are now available in `app.services.historical_data_import_service`. The implementation reads CSV, JSONL, SQLite (read-only URI), Parquet when `pyarrow` is installed, and PostgreSQL. It persists only to a caller-selected `ResearchStore` plus a JSON provenance sidecar. It does not alter source data.

## Backtest, walk-forward, and paper evidence

The previously executed one-session real-data backtest made zero trades and is not performance evidence. Walk-forward remains **NOT TESTED / DATA LIMITATION** for that single session. End-to-end real historical paper-to-ML-to-validation reconciliation remains **NOT TESTED** because the real source fails strict interval certification; no broker credentials or orders were used.

## Security

Live F&O execution is still locked in code: `TRADEPILOT_LIVE_EXECUTION_ENABLED=False`; the execution path returns `PAPER_ONLY` with `LIVE_EXECUTION_DISABLED`. No bypass was added.

## Certification state

**PARTIALLY CERTIFIED.** Runtime code, migration chain, importer/provenance primitives, frontend build, and safety locks have executable evidence. Strict real-data interval validity and multi-session lineage/walk-forward/paper evidence remain outstanding.
