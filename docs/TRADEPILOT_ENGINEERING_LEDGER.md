# TradePilot AI — Engineering Ledger

Repository: varunaradhya/tradepilot-ai
Branch: main
Last updated: 2026-09-29
Current HEAD: lineage-hardening batch in main; exact SHA is reported in the session completion record

## Status
- DONE — implementation complete and verified by available evidence
- IMPLEMENTED — code/tests added; current-head CI verification pending
- PARTIAL — foundation exists; meaningful evidence or integration remains
- BLOCKED — environment/data/credentials required
- LOCKED — safety constraint

| ID | Task | Status | Implementation | Tests | Commit | CI | Remaining risk |
|---|---|---|---|---|---|---|---|
| P0.1 | NSE session/calendar-aware historical validation | IMPLEMENTED | historical_data_service.py, nse_equity_calendar.py, dhan_historical_service.py | test_historical_data_service.py | 59ca4c9 | PENDING | Runtime/CI verification unavailable |
| P0.2 | Trade → ML Learning → Validation reconciliation | IMPLEMENTED | paper_reconciliation_service.py | test_paper_reconciliation.py | 74fc25f | PENDING | Runtime/CI verification unavailable |
| P0.3 | Fresh CI verification | PENDING | .github/workflows/ci.yml exists | N/A | 7fa7b7e | NOT OBSERVED | GitHub integration returned no workflow/status for current push |
| P0.4 | Migration integrity | IMPLEMENTED — CI PENDING | Linear chain through 0016 audited; 0013 SQLite batch alteration; 0014 unique-link constraint; 0015 event time; 0016 ML lineage | Static chain regression added; runtime upgrade/downgrade not executed | c89e548 | PENDING | Fresh/upgrade/downgrade runtime verification still required |
| P1.1 | Historical ingestion hardening | PARTIAL | Dhan path normalized + session-aware; portable import now reuses canonical contract | Import/provenance regression tests added; CI pending | 2fb579e | PENDING | Corporate-action treatment and runtime evidence remain |
| P1.2 | Backtest audit | IMPLEMENTED — CI PENDING | Same-bar execution leakage fixed; next-bar execution; dataset fingerprint + corporate-action state + strategy fingerprint propagated | Regression coverage added | lineage batch | PENDING | Future-high/low, normalization, overlap and runtime evidence remain |
| P1.3 | Walk-forward validation audit | IMPLEMENTED — CI PENDING | Chronological non-overlapping windows plus dataset fingerprint, corporate-action and strategy lineage | Regression coverage added | lineage batch | PENDING | Runtime/OOS evidence remains |
| P1.4 | Strategy framework audit | IMPLEMENTED — CI PENDING | V1/V2/V2A registry plus deterministic strategy fingerprint carried into evidence | Regression coverage added | lineage batch | PENDING | Broader experiment registry provenance remains |
| P1.5 | ML data integrity | IMPLEMENTED — CI PENDING | Temporal event timestamp plus dataset/strategy lineage persisted and required | Regression coverage added | lineage batch | PENDING | Real-data evidence remains |
| P1.6 | ML leakage protection | PARTIAL — CI PENDING | Temporal event ordering hardened; test set removed from qualification gate | Regression coverage added | ed45f12 | PENDING | Broader research leakage suite remains |
| P1.7 | ML lifecycle | PARTIAL | Training/deployment gates exist | Existing tests | — | PENDING | Rollback/version lifecycle audit pending |
| P1.8 | ML evaluation | IMPLEMENTED — CI PENDING | Classification + trade-level metrics + dataset/strategy/schema lineage | Regression coverage added | lineage batch | PENDING | Calibration/real-data evidence remains |
| P1.9 | Portfolio risk engine | IMPLEMENTED | Existing portfolio risk service | Existing tests | — | PENDING | Current-head verification pending |
| P1.10 | Risk consistency | PLANNED | Risk controls exist | — | — | — | Cross-path equivalence audit pending |
| P1.11 | Multi-worker safety | PLANNED | Durable state exists | — | — | — | Restart/concurrency verification pending |
| P1.12 | Idempotency | PARTIAL | Several DB uniqueness boundaries exist | Existing tests | — | PENDING | Full repeated-operation audit pending |
| P1.13 | Restart/recovery | PLANNED | — | — | — | — | Requires runtime environment |
| P1.14 | Live execution hard-lock | LOCKED | production_safety + broker capability constraints | Safety regression suite exists | — | PENDING | Must remain disabled |
| P1.15 | Auth/authorization | PLANNED | Existing auth foundation | — | — | — | IDOR/ownership audit pending |
| P1.16 | Secrets/security | PLANNED | Existing environment configuration | — | — | — | Repo/history/log/Docker audit pending |
| P1.17 | Operational monitoring | PARTIAL | health/audit services exist | — | — | — | Runtime telemetry verification pending |
| P1.18 | Audit trail | PARTIAL | operational audit foundation exists | — | — | — | Coverage audit pending |
| P1.19 | Research dashboard | PARTIAL | Research UI exists | Frontend build pending | — | PENDING | Evidence/reconciliation surfaces need verification |
| P1.20 | Paper dashboard | PARTIAL | Paper UI exists | Frontend build pending | — | PENDING | Risk/freshness/ML display audit pending |
| P1.21 | Indian-market UX | PARTIAL | NSE resolver/search foundations exist | — | — | PENDING | Full-universe UX audit pending |
| P2.1 | Dhan hardening | PARTIAL | Historical + paper integration | Existing tests | — | PENDING | Rate limits/retries/auth/symbol mapping audit |
| P2.2 | Groww/AngelOne foundation | PARTIAL | Capability foundations | — | — | — | No live execution certification |
| P2.3 | Broker abstraction | IMPLEMENTED | Broker capability boundary exists | Existing tests | — | PENDING | Leakage audit pending |
| P2.4 | Portable historical-data import | IMPLEMENTED — CI PENDING | CSV/Parquet/SQLite/PostgreSQL adapters → MarketBar → shared validation → NSE session validation → fingerprint → ResearchStore | Unit/contract tests added | 2fb579e | PENDING | Runtime/CI verification pending; PostgreSQL integration environment not available |
| P2.5 | Real historical evidence | BLOCKED | — | — | — | — | Legitimate market dataset required |
| P2.6 | 30-session real paper validation | BLOCKED | Existing validation framework | — | — | — | Real market data required |
| P2.7 | Cloud readiness | PARTIAL | Docker/PostgreSQL/Alembic configuration exists | Compose CI configured | — | PENDING | Deployment environment verification pending |

## Rules for future sessions

1. Read this ledger and docs/TRADEPILOT_FEATURE_REGISTER.md before changing code.
2. Never repeat an IMPLEMENTED/DONE task without identifying a concrete defect or missing verification.
3. For every implementation change: inspect → implement → regression test → commit → verify.
4. Never mark CI green without an actual current-head result.
5. If a CI run is cancelled, inspect the newest HEAD/run.
6. Keep live broker execution hard locked.
7. Never fabricate market data, backtest results, profitability, broker certification, or CI results.
8. Prefer shared contracts over parallel validation implementations.


## Latest lineage hardening — 2026-09-29
- Added explicit corporate-action state to lineage-backed backtests and walk-forward results.
- Added strategy fingerprint and dataset fingerprint to backtest trade evidence.
- Persisted dataset/strategy fingerprints on paper ML learning events.
- Added migration 0016 for ML lineage fields.
- ML training now fails closed on missing/mixed strategy lineage or missing/mixed dataset lineage.
- ML models persist aggregate training-dataset fingerprint, strategy fingerprint and feature-schema fingerprint.
- Added regression tests for lineage aggregation, training rejection and migration chain.
- CI remains unverified.


### 2026-09-29 — Authorization boundary hardening
- Found a legacy authenticated-but-unguarded `/paper-session/bar` mutation path with separate in-memory state.
- Disabled legacy `/paper-session/bar` and `/paper-session/reset` mutations with HTTP 410.
- Preserved the durable `/paper-trading/session/*` pipeline as the supported mutation path.
- Added regression contract coverage.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Paper-only safety hardening
- Disabled remaining `/paper-trading/session/bar`, `/paper-trading/session/reset`, and `/paper-trading/session/market-reset` mutation paths with HTTP 410.
- These legacy/destructive routes no longer provide alternate state mutation outside the hardened server-controlled market-bar/signal pipeline.
- Hardened the F&O execution adapter to fail closed regardless of configuration and never submit a Dhan broker order.
- Added regression contracts for the disabled routes and broker-execution fail-closed boundary.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Safety/concurrency hardening continuation
- Enforced persisted strategy authorization and fingerprint parity for F&O paper entry.
- Serialized paper market-state read/write boundaries with row locks and uniqueness-race recovery.
- Added regression coverage for F&O authorization parity.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Mutation concurrency hardening
- Locked owned `PaperTrade` rows before direct mark/close mutation.
- Serialized strategy authorization upserts and added uniqueness-race recovery.
- Added regression contracts for both boundaries.
- Status: IMPLEMENTED — CI PENDING.

### 2026-09-29 — Broker security hardening
- Serialized broker connection upserts and recovered uniqueness races.
- Locked sync metadata updates and sanitized persisted sync messages.
- Removed broker credential access from the already-disabled F&O execution endpoint.
- Added regression contracts.
- Status: IMPLEMENTED — CI PENDING.

### 2026-09-29 — F&O close concurrency hardening
- Locked owned option paper positions before manual close.
- Added regression contract.
- Status: IMPLEMENTED — CI PENDING.

### 2026-09-29 — CI verification hardening
- CI Alembic verification now explicitly targets an isolated SQLite database.
- Latest GitHub commit status/workflow queries still return no checks or workflow runs.
- Status: WORKFLOW CONFIGURED — EXECUTION NOT VERIFIED.


### 2026-09-29 — F&O duplicate-entry and close-state hardening
- F&O paper entry now requests a row lock on the active strategy authorization before checking for an existing open option position, closing a duplicate-position read/insert race within the authorization boundary.
- Paper trade close now checks the conditional update row count and refreshes the canonical trade when another transaction won the close race.
- Regression contracts added for both invariants.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Broker order retry safety
- Dhan order placement now explicitly disables automatic HTTP retries to avoid duplicate-order risk after ambiguous broker responses.
- Generic retry behavior remains available for non-order broker calls.
- Added regression coverage for the explicit retry policy.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Portfolio synchronization hardening
- Serialized Dhan portfolio syncs by locking the ownership-scoped broker connection before fetching/applying the broker snapshot.
- Stopped importing transactions with malformed broker timestamps rather than synthesizing a new timestamp that could defeat repeat-sync deduplication.
- Added regression contracts for both invariants.
- Status: IMPLEMENTED — CI PENDING.
