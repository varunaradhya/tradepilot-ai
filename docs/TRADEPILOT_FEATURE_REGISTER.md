# TradePilot AI — Feature & Development Register\n\n**Purpose:** Single source of truth for implemented, defective, partial, planned and intentionally locked TradePilot capabilities.\n**Repository:** varunaradhya/tradepilot-ai  \n**Last audited:** 2026-09-29  \n**Audit source:** GitHub repository source and commit history. Runtime execution was not performed during this audit.\n\n> Mandatory: Before any feature work, read this register and docs/TRADEPILOT_RULEBOOK.md. Do not recreate an existing feature.\n\n## Status legend\n- DONE — CI VERIFIED\n- IMPLEMENTED — CI PENDING\n- PARTIAL\n- DEFECT FOUND\n- BLOCKED — ENVIRONMENT\n- PLANNED\n- LOCKED BY SAFETY POLICY\n\n## Current baseline\nTradePilot contains a mature paper-first foundation covering market-data boundaries, paper trading, research/backtesting, strategy registry, ML learning infrastructure, multi-symbol validation, operational safety, monitoring, broker foundations and deployment configuration.\nA supplied historical SQLite dataset is available for structural validation, but remains quarantined/not certified because data-quality and corporate-action provenance gates are not yet satisfied.\n\n## Capability register\n| ID | Capability | Status | Notes |\n|---|---|---|---|\n| TP-001 | NSE/Indian equity boundary | IMPLEMENTED — CI PENDING | Server-side validation; current-head CI still needs confirmation |\n| TP-002 | Paper trading engine | IMPLEMENTED — CI PENDING | Simulation only |\n| TP-003 | Paper risk controls | IMPLEMENTED — CI PENDING | Risk/allocation/daily-loss/position controls |\n| TP-004 | Durable paper/session state | IMPLEMENTED — CI PENDING | Session and market state persistence |\n| TP-005 | Dhan historical ingestion | IMPLEMENTED — CI PENDING | Historical research/paper path |\n| TP-006 | Historical session idempotency | IMPLEMENTED — CI PENDING | DB uniqueness boundary |\n| TP-007 | Research dataset store | IMPLEMENTED — CI PENDING | Atomic save + incremental merge |\n| TP-008 | Research data-quality validation | IMPLEMENTED — CURRENT HEAD CI GREEN | Generic contract plus NSE session/calendar-aware validation; current-head CI still pending |\n| TP-009 | Intraday backtest | IMPLEMENTED — CI PENDING | Runtime real-data evidence still required |\n| TP-010 | Walk-forward research | IMPLEMENTED — CI PENDING | Runtime real-data evidence still required |\n| TP-011 | Research experiment lineage | IMPLEMENTED — CI PENDING | Persistent experiment records |\n| TP-012 | Corporate-action infrastructure | IMPLEMENTED — CI PENDING | Real corporate-action dataset still required |\n| TP-013 | Strategy registry | IMPLEMENTED — CI PENDING | V1/V2/V2A |\n| TP-014 | V1/V2/V2A research comparison | IMPLEMENTED — CI PENDING | Current-head CI required |\n| TP-015 | Portfolio risk gate | IMPLEMENTED — CI PENDING | Invalid existing position/config inputs now fail closed; current-head verification still required |\n| TP-016 | ML learning ledger | IMPLEMENTED — CI PENDING | Requires real data for meaningful evidence |\n| TP-017 | ML model training | PARTIAL | Infrastructure exists; real training evidence unavailable |\n| TP-018 | ML paper deployment | PARTIAL | Gates exist; forward evidence unavailable |\n| TP-019 | ML live deployment | LOCKED BY SAFETY POLICY | Must remain disabled |\n| TP-020 | 30-session validation ledger | IMPLEMENTED — CI PENDING | Infrastructure exists |\n| TP-021 | Multi-symbol validation | IMPLEMENTED — CI PENDING | Current-head CI required |\n| TP-022 | NSE equity calendar | IMPLEMENTED — CURRENT HEAD CI GREEN | Explicit regular/live-special/mock/holiday/unknown classification and source-backed exceptional-session windows |\n| TP-023 | Validation manifest/hash chain | IMPLEMENTED — CI PENDING | Tamper-evident, not immutable |\n| TP-024 | Validation readiness gate | IMPLEMENTED — CI PENDING | Real data still required |\n| TP-025 | Broker capability abstraction | IMPLEMENTED — CI PENDING | Dhan foundation; Groww/AngelOne foundation-only |\n| TP-026 | External broker sandbox certification | BLOCKED — ENVIRONMENT | Requires credentials/provider environment |\n| TP-027 | Cloud readiness diagnostics | IMPLEMENTED — CI PENDING | Deployment environment still needs verification |\n| TP-028 | External monitoring/alert delivery | BLOCKED — ENVIRONMENT | Requires external delivery infrastructure |\n| TP-029 | Backup/restore drill | IMPLEMENTED — CI PENDING | Guarded PostgreSQL backup/restore drill script added; actual production drill still requires deployed database |\n| TP-030 | TLS/network verification | BLOCKED — ENVIRONMENT | Requires deployment environment |\n| TP-031 | Shared historical-data contract | IMPLEMENTED — CURRENT HEAD CI GREEN | Normalize/validate contract now includes NSE session/calendar diagnostics and source-timezone consistency |\n| TP-032 | NSE-equity resolver reuse | IMPLEMENTED — CI PENDING | Shared resolver added and research/paper Dhan paths migrated |\n| TP-033 | Transactional trade/learning persistence | IMPLEMENTED — CI PENDING | Learning event can participate in caller transaction; Dhan paper path now commits trade + learning together |\n| TP-034 | Alembic model metadata completeness | IMPLEMENTED — CI PENDING | P10 validation models registered in Alembic metadata; PostgreSQL migration upgrade/downgrade now covered in CI |\n| TP-035 | Dataset version/fingerprint in all research results | IMPLEMENTED — CI PENDING | Backtest/walk-forward evidence carries validated dataset fingerprint and explicit corporate-action state; ML training models carry aggregate dataset lineage |\n| TP-036 | Leakage/look-ahead regression suite | PARTIAL — CI PENDING | Same-bar execution, temporal ordering, overlap and backtest-input guards added; broader future-data coverage remains |\n| TP-037 | ML trading-aware evaluation | IMPLEMENTED — CI PENDING | Validation/test results include trade metrics; qualification remains validation-only and model training now requires complete dataset/strategy lineage |\n| TP-038 | ML/data drift monitoring | PLANNED | Future research/operations |\n| TP-039 | Trade/learning/validation reconciliation | IMPLEMENTED — CI PENDING | Three-ledger invariants added; current implementation remains evidence/readiness gated |\n| TP-040 | Groww production-grade integration | PARTIAL | Foundation only |\n| TP-041 | AngelOne production-grade integration | PARTIAL | Foundation only |\n| TP-042 | CSV/Parquet/SQLite/PostgreSQL data import | IMPLEMENTED — CURRENT HEAD CI GREEN | Shared MarketBar normalization, quality validation, NSE session checks, fingerprinting and ResearchStore provenance |\n| TP-043 | Real historical evidence | BLOCKED — ENVIRONMENT | Requires legitimate market dataset |\n| TP-044 | 30-session real paper validation | BLOCKED — ENVIRONMENT | Requires real market data |\n| TP-045 | Strategy qualification from real evidence | BLOCKED — ENVIRONMENT | Must remain evidence-gated |\n| TP-046 | Live trading | LOCKED BY SAFETY POLICY | No live orders |
| TP-047 | Strategy parameter provenance | IMPLEMENTED — CI PENDING | Strategy fingerprints propagate from backtest trades into learning events; mixed/missing strategy lineage blocks ML training |
| TP-048 | ML dataset/model lineage | IMPLEMENTED — CI PENDING | Learning events and models persist dataset, strategy and feature-schema fingerprints; mixed/missing dataset lineage blocks training |
| TP-049 | Corporate-action state consistency | IMPLEMENTED — CI PENDING | Lineage-backed backtests require explicit adjusted/unadjusted state and propagate it through walk-forward evidence |\n\n## Permanent constraints\n1. India/NSE first.\n2. Intraday first.\n3. Paper first.\n4. Risk before execution.\n5. Evidence before promotion.\n6. Never optimize against OOS data.\n7. Never use future information in signal/backtest calculations.\n8. Never fabricate data or results.\n9. Never treat missing CI evidence as a pass.\n10. Live execution remains locked.\n11. Existing functionality must be checked before new implementation.\n\n## Current P0 backlog\n1. Fresh CI verification of current HEAD.\n2. Fresh/upgrade/downgrade/recovery verification of the Alembic chain.\n3. Add portable historical-data import.\n4. Obtain legitimate historical data for evidence runs.\n8. Obtain real historical data.\n9. Run data-quality validation.\n10. Run backtest/cost sensitivity/walk-forward/OOS.\n11. Complete 30-session real paper validation.\n\n## Current P1 backlog\n- Research leakage/look-ahead suite.\n- Dataset versioning/fingerprinting.\n- Strategy parameter provenance.\n- Corporate-action real-data validation.\n- ML trading-aware evaluation.\n- ML/data drift.\n- Cross-ledger reconciliation.\n- External monitoring.\n- Backup/restore drill.\n- TLS/network deployment verification.\n- Real broker sandbox verification.\n- PostgreSQL multi-worker verification.\n- Migration upgrade/recovery testing.\n\n## Current P2/P3 backlog\n- Groww/AngelOne full integrations.\n- Broader market universe.\n- Options/F&O research.\n- Portfolio attribution.\n- Advanced Research UI.\n- Cloud data pipeline.\n- Production deployment hardening.\n- Independent safety review.\n\n## Change history\n### 2026-09-29 — Audit baseline\n- Re-audited repository after P10 and subsequent V2/V2A research work.\n- Identified stale prior register.\n- Added mandatory Rulebook.\n- Added explicit audit findings and pending-task IDs.\n- Added anti-duplication workflow.\n- Added current data-unavailability status.\n\n### 2026-09-29 — P0 hardening batch 1\n- Registered P10 validation models in Alembic metadata.\n- Added shared NSE-equity instrument resolver and migrated research/paper Dhan paths.\n- Added transaction-aware ML learning-event persistence and coupled it to Dhan paper trade commit.\n- Hardened research timestamp parsing and expected-interval gap diagnostics.\n- Added regression tests for invalid timestamps and interval gaps.\n- Status: IMPLEMENTED — CI PENDING.\n

### 2026-09-29 — P0 hardening batch 2
- Unified the core historical data normalization/validation contract with timezone normalization and expected-interval gap diagnostics.
- Applied interval-aware validation to Dhan intraday history.
- Added dedicated regression coverage for interval gaps and timezone-aware normalization.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — P0 hardening batch 3
- Added durable nullable learning-event foreign-key linkage to paper trades.
- Dhan paper persistence now flushes and links the learning event before committing the trade.
- Added paper learning reconciliation service and validation API endpoint.
- Added regression tests for linked/unlinked paper trades.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Portable import/provenance batch
- Audited the full Alembic revision chain through 0014; no duplicate revision IDs or visible branch conflicts were found.
- Added a static migration-chain regression test; runtime upgrade/downgrade remains unverified until CI/runtime execution is available.
- Added CSV, Parquet, SQLite and PostgreSQL historical import adapters.
- Reused the canonical MarketBar normalization and historical quality contract rather than introducing a second validator.
- Added deterministic SHA-256 dataset fingerprints and provenance sidecars.
- Attached provenance to Dhan daily research datasets.
- Added regression tests for import, provenance, unsafe table identifiers and migration ordering.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Leakage hardening batch
- Added explicit `event_at` to paper ML learning events and migration 0015.
- Learning-event creation now requires a trustworthy entry/signal timestamp.
- ML training orders observations by feature event time, not persistence ID.
- Training fails closed if historical events lack feature timestamps.
- Model qualification now uses validation metrics only; final test metrics are report-only.
- Added regression coverage for temporal ordering, timestamp requirements and qualification behavior.


### 2026-09-29 — Same-bar execution leakage hardening
- Audited the intraday backtest execution boundary.
- Found that signals derived from a completed bar were filled using that same bar's close.
- Changed research execution to queue the signal and fill at the next bar's open.
- Final-bar signals are not executable because no next bar exists.
- Added regression coverage proving a signal reference of 100 followed by a 110 open produces a fill based on the next bar.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — ML evaluation hardening
- Fixed the temporal event timestamp runtime import.
- Added trade-aware evaluation metrics to validation/test reporting.
- Kept the final test set report-only and unchanged as a qualification input.
- Added regression coverage for P&L, expectancy, win rate and average R-multiple.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Dataset lineage hardening
- Added validated dataset fingerprint input to intraday backtests.
- Backtest results now return the exact dataset fingerprint used by the evidence run.
- Fixed-parameter walk-forward propagates the fingerprint through V1/V2 results and top-level output.
- Added regression coverage for fingerprint validation and propagation.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Lineage hardening batch
- Backtest evidence now requires explicit corporate-action state whenever a dataset fingerprint is supplied.
- Backtest trades carry strategy and dataset lineage.
- Paper learning events persist dataset and strategy fingerprints.
- ML training rejects missing/mixed strategy or dataset lineage.
- Persisted ML models now record aggregate training-dataset fingerprint, strategy fingerprint and feature-schema fingerprint.
- Added migration 0016 and regression coverage.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Authorization boundary hardening
- Disabled legacy paper-session mutation endpoints that could bypass persisted strategy authorization, readiness and durable recovery controls.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Paper-only safety hardening
- Disabled remaining legacy/destructive paper-session mutation endpoints in the main paper-trading router.
- Hardened F&O execution so configuration cannot enable broker order submission.
- Added regression contracts for both safety boundaries.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Safety/concurrency hardening continuation
- Enforced persisted strategy authorization and fingerprint parity for F&O paper entry.
- Serialized paper market-state read/write boundaries with row locks and uniqueness-race recovery.
- Added regression coverage for F&O authorization parity.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Mutation concurrency hardening
- Direct paper-trade mark/close mutations now lock the owned row before mutation.
- Strategy authorization updates now handle concurrent upsert races safely.
- Added regression coverage.
- Status: IMPLEMENTED — CI PENDING.

### 2026-09-29 — Broker security hardening
- Broker connection mutation path is concurrency-safe.
- Disabled F&O execution no longer decrypts broker credentials.
- Regression coverage added.
- Status: IMPLEMENTED — CI PENDING.

### 2026-09-29 — F&O close concurrency hardening
- Manual option close now uses an ownership-scoped row lock.
- Status: IMPLEMENTED — CI PENDING.

### 2026-09-29 — CI verification hardening
- Fresh migration CI step now uses explicit isolated SQLite configuration.
- GitHub execution remains unverified because no workflow run/check is exposed for the latest commit.


### 2026-09-29 — Paper mutation concurrency hardening continuation
- F&O paper-entry authorization reads can now be explicitly locked; the F&O entry path uses the lock before its duplicate open-position check.
- Paper trade close detects lost conditional updates and returns refreshed canonical state instead of implying that its own mutation won.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Broker order retry safety
- Disabled automatic retries specifically for broker order placement while retaining retries for other Dhan API operations.
- This preserves the paper/live safety boundary against future duplicate-order risk.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Portfolio consistency hardening
- Dhan portfolio synchronization now uses a durable broker-connection row lock to serialize concurrent syncs.
- Malformed broker-supplied trade timestamps are rejected instead of generating unstable local identities.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Portfolio holding uniqueness hardening
- Identified a concrete duplicate-position risk in the manual holding path: no database constraint enforced one holding per `(user_id, symbol)`.
- Added the unique database boundary plus controlled conflict handling for concurrent/manual duplicate creation.
- Existing duplicate rows are not silently merged by the migration; explicit reconciliation is required if they exist.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Portfolio transaction concurrency hardening
- Transaction create/update/delete now serialize the user-wide holding rebuild using a durable user-row lock.
- This closes a cross-worker race where concurrent transaction mutations could interleave full holding reconstruction.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Authentication and deployment security hardening
- Password changes now invalidate previously issued access/refresh tokens through durable password-change timestamps.
- Production refuses the known development JWT secret; automatic schema creation defaults off in favor of Alembic.
- Dhan provider errors/retry logs are sanitized to avoid leaking provider payloads or exception details.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-30 — Research-engine boundary audit
- Walk-forward window builder now emits a valid single window when the dataset exactly fits train + validation sizes.
- Overlapping validation windows are rejected by default.
- Added regression coverage for exact-fit and overlap behavior.
- Added an auditable India-equity intraday fee calculator with explicit brokerage, exchange/IPFT, SEBI turnover, STT, stamp duty and GST inputs.
- The fee schedule is explicit/versioned rather than silently treating brokerage-only simulation as complete statutory-cost modeling.
- Backtest session-boundary hardening is recorded in the engineering ledger and dedicated audit document.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-30 — ML/reconciliation audit continuation
- ML temporal ordering now permits equal event timestamps under deterministic event-time-plus-ID ordering.
- Paper reconciliation orphan detection now includes learning events attached to open Dhan paper trades.
- No new performance qualification is granted by these code changes.
- Status: IMPLEMENTED — CI PENDING.


## 2026-09-30 hardening additions

- **Backtest input contract:** strict timestamp ordering/uniqueness, timezone-awareness consistency, OHLC validation, and single-symbol enforcement.
- **Backtest cost accounting:** explicit versioned India-equity intraday fee schedule integrated into entry/exit cash and P&L, with per-trade fee evidence.
- **Execution safety regressions:** gap-through-stop, conservative same-bar stop/target ordering, and daily-loss halting.
- **Deployment safety:** explicit production secrets/CORS, backend readiness healthcheck, Compose dependency ordering, and Python runtime alignment with CI.
- **Recovery documentation:** production backup/restore and runtime-drill runbook.


### 2026-10-01 — Independent safety hardening continuation
- Portfolio risk now rejects malformed existing positions and invalid risk configuration instead of silently clamping unsafe values.
- Execution idempotency now records explicit keys only after all order authorization gates pass.
- Operational audit-event API reads are user-scoped.
- These changes are separate from the completed research-certification/data-quality workstream.


### 2026-10-01 — Current-head verification and session-calendar completion
- Verified GitHub Actions run **1746** for current HEAD `8828c96a99f6d3e0ca997530408184866a3d359a`: all required CI jobs succeeded.
- Completed the source-backed NSE exceptional-session boundary used by research certification, including documented Muhurat sessions and explicit rejection of unknown weekend sessions.
- Re-ran structural checks against the supplied intraday dataset: 0 unknown weekend rows and 0 outside-known-window rows; 18 negative-volume rows remain.
- The dataset is still not certified. No profitability or strategy-performance qualification is granted.


### 2026-10-01 — NSE holiday calendar completion
- Added the remaining NSE-published 2026 equity holidays currently relevant to the loaded annual calendar: 19-Feb, 19-Mar, 01-Apr and 26-Aug.
- Added regression coverage and verified current HEAD with GitHub Actions run 1753.
- Future special-session timing is not invented when the exchange has not published the window.
