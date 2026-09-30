# TradePilot AI Runtime Certification

## Scope and environment

Certification was executed on Windows at commit `82b67efd7eb81756da60c68ddcc9a97a89b3b895` using Python 3.12.10 in an isolated `backend/.venv-certification` environment. Docker was unavailable and was not used. Raw market data and the original SQLite database were not modified.

This document preserves historical certification and forensic evidence. Its inclusion on a later reconciled branch is not a new real-data certification of that branch.

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

The original issue was that `paper_trades` had to exist before revision `20260821_0005` added option columns. Current `main` repairs that fresh-database path in revision `20260821_0005` with a conditional base-table creation. Its current revision `20260928_0009` has no duplicate explicit SQLite index creation.

## Real historical data

The local Dhan-derived NSE dataset `equity_nse_discovery_5m` contains 20 equity symbols, 1,825,166 clean rows and 29,804 quarantined rows according to its existing manifest. The original files were read only.

The first isolated TCS exercise used 76 rows for 2021-08-16 from the clean TCS partition. Generic OHLC, volume, duplicate, chronological-order, and ResearchStore persistence checks passed. Its deterministic SHA-256 fingerprint was `40d69c6a5804b5c8e135b3d73a09bcc6f60518fe716070e29fd6a5ac6d222098`; a re-read produced the same fingerprint. Corporate-action state is `UNKNOWN`.

### Data limitation: timestamp interval irregularity

The TCS source is not strictly certifiable as 5-minute bars. 43 of 75 adjacent intervals were not exactly 300 seconds; observed deltas ranged from 239 to 361 seconds. No timestamps were rounded, resampled, repaired, or removed. The session had 76 accepted boundary/count bars (09:15–15:30 Asia/Kolkata), but strict interval validation remains a **DATA LIMITATION**.

## Real Data Timestamp Forensics

### Source and lineage

**PASS — source identified.** The original source is the read-only SQLite database `D:\tradepilot-ai\backend\data\research\market_data.sqlite` (1,993,109,504 bytes; last modified 2026-08-17). Its `equity_bars` schema is `dataset_id TEXT, symbol TEXT, timestamp INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL`, keyed by `(dataset_id, symbol, timestamp)`. Dataset metadata describes `equity_nse_discovery_5m` as source `Dhan`, interval `5`, NSE equity OHLC/volume data from 2021-08-16 through 2026-08-16.

Lineage is: Dhan historical-intraday response arrays → `download_equity_research.py` (row-wise array pairing) → `ResearchDataCache.put_equity` (direct `int(timestamp)` persistence) → read-only dataset builder → symbol-partitioned JSONL → isolated certification store. The downloader and cache do not convert timezone, round timestamps, resample, interpolate, or synthesize bars. The partition builder converts each stored epoch to Asia/Kolkata only for classification and emits the same instant as ISO-8601.

### Examined sessions and interval evidence

**FAIL — strict 5-minute contract for affected sessions.** TCS, INFY, RELIANCE, AXISBANK, and HDFCBANK were each examined across an early session, a mid-range session, and a late session. For all five symbols, 2021-08-16 had 75 or 76 regular-session rows but mixed deltas of approximately 239–361 seconds, non-zero seconds components, and missing/unexpected clock-grid slots. For example, TCS began `09:15:00`, then `09:21:00` (+360), `09:26:00` (+300), `09:30:00` (+240), and continued with compensating 4/6-minute shifts. TCS had 32 exact 300-second deltas, 22 below 300, and 21 above 300; 29 expected 09:15–15:25 slots were absent and 30 unexpected timestamps were present (the extra row was the allowed 15:30 terminal observation). There were no duplicate timestamps.

For that TCS session, the exact delta distribution was `239:1, 240:7, 241:4, 299:10, 300:32, 301:9, 358:1, 359:1, 360:9, 361:1`; timestamp seconds were `0:60, 1:15, 2:1`. These are source epochs, not timestamps reconstructed by TradePilot.

In contrast, sampled sessions on 2024-02-08/09 and 2026-07-31 for the same symbols had 75 rows, all 74 adjacent deltas exactly 300 seconds, zero-second timestamps, and no missing or unexpected expected slots.

Across all accepted full sessions, TCS had 1,196 strict sessions and 19 irregular sessions out of 1,215; INFY had 1,196/1,215; RELIANCE had 1,195/1,214; AXISBANK and HDFCBANK each had 1,196/1,215. The same 19 irregular full-session dates occurred for TCS, INFY, and RELIANCE: 2021-08-16/17/18/20/23/24/25/26/27/31; 2021-09-03/06/07/08/13/14/15/17; and 2022-01-27. This is dataset-wide/upstream behavior, not TCS-specific.

**FAIL — no fixed-offset model.** A UTC/IST conversion or any other fixed timestamp offset preserves adjacent deltas, so it cannot convert 240/360-second pairs into a 300-second grid. The early affected sessions mix grid-aligned timestamps, +1-second jitter, and +60-second minute shifts within a single symbol/session. Therefore the source does not use a coherent bar-start, bar-end, UTC, or local-time convention that can be safely normalized with one documented offset. No timestamp transformation is justified.

### Missing versus irregular bars

**DATA LIMITATION.** Affected sessions retain the expected *count* of observations but do not retain the expected clock grid. The evidence establishes missing and unexpected timestamp slots; it does not establish whether a provider emitted bars with incorrect timestamps or whether an economically distinct bar is absent, because original per-bar provider payloads were not retained. TradePilot must treat affected sessions as invalid for strict 5-minute research rather than infer or fill their intended slots.

### Quarantine evidence

**PASS — quarantined rows remain excluded.** The 29,804 quarantine rows comprise 22,020 `PARTIAL_SESSION`, 7,316 `WEEKEND`, 468 `OUTSIDE_REGULAR_SESSION`, and 18 `NEGATIVE_VOLUME` reasons. No `INVALID_OHLC`, duplicate-timestamp, malformed-timestamp, or interval-specific rows were quarantined by the existing builder. For TCS: 1,006 partial-session rows, 370 weekend rows, 24 outside-regular-session rows, and one negative-volume row. Partial-session dates (for example 2021-08-30, 2021-09-01/02, 2021-09-09, and later truncated dates) are distinct from the 19 timestamp-irregular sessions; the quarantine process therefore neither caused nor corrected the observed full-session timestamp problem.

### Data-contract conclusion

**DATA QUALITY FAILURE — strict 5-minute data contract.** The original source’s epoch timestamps are irregular before any TradePilot processing, and the issue affects multiple symbols on the same dates. The dataset must not be used as one strict 5-minute historical series. Strictly on-grid sessions may be selected only after per-session validation, preserving the raw source and the rejection evidence. The validator should **not change**: accepting row counts/boundaries alone is insufficient, and no legitimate documented source convention was demonstrated.

### Strict-valid session certification

**PASS — deterministic raw-session classification.** `scripts/certify_strict_nse_sessions.py` reads the existing symbol-partitioned JSONL source and records, for every symbol/date, row count, first/last timestamp, exact 300-second interval evidence, generic quality diagnostics, NSE calendar diagnostics, per-session SHA-256 content/dataset fingerprint, and corporate-action state. It does not modify source data or timestamps. The local reproducible manifest was written to the ignored runtime path `backend/.runtime-certification/strict_nse_5m_session_manifest.json`.

The scan classified 2,840 of 24,274 sessions as `STRICT_VALID` and 21,434 as `INVALID`. Each of the 20 symbols had 142 strict-valid sessions; the remaining invalid-session counts range from 1,066 (ITC) to 1,073. The strict subset is an eligibility filter, not a repair of the broader **DATA QUALITY FAILURE**.

### Corporate-action lineage investigation

**BLOCKED — source adjustment state remains unavailable.** The current provenance model stores `corporate_action_adjusted` as an optional field, and the repository contains corporate-action infrastructure (`corporate_actions` table plus adjustment-factor helpers), but the certified Dhan-derived dataset has no source-backed adjustment-state field and no dataset-linked corporate-action record was identified that can establish whether these intraday OHLC values are adjusted or unadjusted.

The Dhan historical-data API documentation describes the intraday response as OHLC, volume, and epoch timestamp data, but does not document an adjustment-state field or a parameter establishing that the returned intraday candles are corporate-action-adjusted. Therefore the provider documentation is not sufficient evidence to assign `ADJUSTED` or `UNADJUSTED` to the stored dataset. urlDhanHQ Historical Data API documentationhttps://dhanhq.co/docs/v2/historical-data/

No corporate-action state was inferred from prices, symbol history, or the existence of the corporate-actions table. The correct state for the certified source remains **UNKNOWN**.

### Strict-subset research and validation status

**NOT TESTED / DATA LIMITATION — lineage-aware real-data backtest, walk-forward, and PaperTrade → PaperMlLearningEvent → ValidationEvidence reconciliation.** A fixed three-session TCS strict-valid sample (`2026-01-01`, `2026-01-02`, `2026-01-05`) was selected deterministically. Each session has 75 exact-grid bars and a per-session fingerprint, but all carry corporate-action state `UNKNOWN`. The existing backtest lineage contract correctly rejects a fingerprinted run without explicit `corporate_action_adjusted` state. Assigning `True` or `False` would fabricate unavailable source metadata, so no P&L result, walk-forward result, paper/ML linkage, or performance claim was produced.

The implementation continues to enforce completed-bar signals with `NEXT_BAR_OPEN` execution and prohibits a final-bar executable trade. Existing focused regression coverage validates those guards, but it does not turn the blocked real-data lineage exercise into performance evidence.

## Verification of current certification branch

**PASS — GitHub CI verified for current strict-session certification commit.** GitHub Actions run **1585** for commit `84a12e18efd84d88725245a023d322da7b05a628` completed successfully. Backend, frontend, deployment-config, and release-gate jobs all reported success. The backend job completed compile, fresh Alembic migration, and backend test execution successfully; the frontend job completed dependency installation and production build successfully.

This current-head CI result supersedes the earlier local full-suite stall as the authoritative repository-level regression evidence for commit `84a12e18efd84d88725245a023d322da7b05a628`. The exact local pytest count is not asserted here because the local runner did not complete reliably.

## Historical import and provenance

The current import/provenance implementation uses `HistoricalImportRequest`, `DatasetProvenance`, deterministic `fingerprint_market_bars`, and the `import_rows`/format-specific import functions in `app.services.historical_data_import_service`. It persists imported data and provenance only to a caller-selected `ResearchStore`; source data is not altered.

Importer safety follow-up on `certification-sync`: **JSONL PASS** — one JSON object per non-empty line is accepted through the same normalization, generic/NSE validation, fingerprint, provenance, and `ResearchStore` pipeline as CSV. Malformed JSONL and invalid/missing market-bar fields are rejected; no malformed line is silently skipped. **SQLite READ-ONLY PASS** — SQLite sources are opened with SQLite's `mode=ro` URI mechanism, and regression coverage verifies that the importer reads the expected rows while source schema and rows remain unchanged and write statements are rejected. **Parquet OPTIONAL / NOT RUNTIME-TESTED** — support remains conditional on `pyarrow`; its absence produces a clear dependency error. **PostgreSQL IMPLEMENTED / NOT RUNTIME-TESTED** — the interface remains available, but no external PostgreSQL server was used for certification.

## Backtest, walk-forward, and paper evidence

The previously executed one-session real-data backtest made zero trades and is not performance evidence. Walk-forward remains **NOT TESTED / DATA LIMITATION** for that single session. End-to-end real historical paper-to-ML-to-validation reconciliation remains **NOT TESTED** because the real source lacks explicit corporate-action adjustment state; no broker credentials or orders were used.

## Security

Live F&O execution is still locked in code: `TRADEPILOT_LIVE_EXECUTION_ENABLED=False`; the execution path returns `PAPER_ONLY` with `LIVE_EXECUTION_DISABLED`. No bypass was added.

## Certification state

The current branch is **PARTIALLY CERTIFIED**:

- Historical importer safety: **PASS**
- Strict raw NSE session classification: **PASS**
- Broad Dhan-derived 5-minute dataset: **DATA QUALITY FAILURE**
- Strict-valid session research qualification: **BLOCKED — corporate-action state UNKNOWN**
- Real-data backtest performance evidence: **NOT ESTABLISHED**
- Walk-forward: **NOT TESTED / DATA LIMITATION**
- Paper/ML/validation reconciliation: **NOT TESTED / DATA LIMITATION**
- Live execution: **LOCKED**

The next legitimate research-enablement step is to obtain source-backed corporate-action adjustment metadata for the dataset (or import a separately documented dataset whose adjustment state is explicit). The lineage contract should not be weakened to make the current source pass.

## 2026-09-30 engineering audit continuation

The certification branch was extended with additional research-engine integrity hardening:

- Backtest session-boundary safety: pending signals cannot cross an NSE session; intraday positions flatten at session end by default.
- Walk-forward exact-fit handling: a dataset whose length exactly equals train + validation now yields one valid window.
- Walk-forward overlap protection: validation windows cannot overlap.
- India-equity fee model: explicit/versioned fee inputs now exist for brokerage, NSE transaction/IPFT, SEBI turnover, STT, stamp duty and GST. The fee model does not by itself certify a historical fee schedule; the effective-date schedule must match the research period.
- ML temporal ordering: simultaneous event timestamps are allowed when deterministic event-time-plus-ID ordering is preserved; only backwards event-time movement is rejected.
- Paper reconciliation: learning events attached to still-open Dhan paper trades are no longer falsely classified as orphan events.

These changes are engineering hardening only. They do not establish strategy profitability or real-market qualification.

### Certification status remains unchanged

- Historical importer safety: PASS by source/code evidence; current-head CI must be verified.
- Strict raw NSE session classification: PASS for the classifier contract.
- Broad Dhan-derived five-minute dataset: DATA QUALITY FAILURE due source timestamp irregularities.
- Corporate-action state for the certified Dhan-derived dataset: UNKNOWN.
- Real-data backtest performance evidence: NOT ESTABLISHED.
- Walk-forward performance evidence: NOT ESTABLISHED.
- ML performance evidence: NOT ESTABLISHED.
- PaperTrade → ML → Validation reconciliation: code contract exists; real-data execution evidence NOT ESTABLISHED.
- Live execution: LOCKED.

## 2026-09-30 — Current-head CI and hardening verification

The certification-sync branch was re-verified through GitHub Actions run **1646** for commit `f7fd9af8848087014f7aab29e8e2f6a4f5b5fda9`.

- Backend: **PASS** — dependency installation, compile, fresh Alembic migration, and full backend test suite completed successfully.
- Frontend: **PASS** — dependency installation and production build completed successfully.
- Deployment-config: **PASS** — Docker Compose configuration validated with explicit CI secrets/CORS.
- Release-gate: **PASS**.
- Full backend result: **835 passed, 1 skipped, 102 warnings** in the final successful run.

This verifies the current repository hardening commit. It does **not** remove the real-data certification blockers documented above.

The backtest audit now additionally enforces:
- timestamp ordering/uniqueness when timestamps are supplied,
- single-symbol consistency when symbol metadata is supplied,
- malformed OHLC rejection,
- explicit fee integration,
- gap-through-stop behavior,
- conservative same-bar stop/target ordering,
- daily-loss entry halting.

The production/deployment hardening now includes explicit PostgreSQL password/CORS requirements, backend readiness health checks, Compose dependency ordering, Python 3.12 alignment with CI, and a documented backup/restore/runtime-drill procedure.

### Current certification state

**PARTIALLY CERTIFIED / NOT READY TO MERGE**

Engineering CI is green for the current head. The remaining research blocker is still source-backed corporate-action adjustment metadata (or a separately documented dataset with explicit adjustment state). Production runtime/backup/restore drills remain environment-dependent. Live execution remains locked.
