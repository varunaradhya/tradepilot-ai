# TradePilot AI — Engineering Ledger

Repository: varunaradhya/tradepilot-ai
Branch: main
Last updated: 2026-10-01
Current HEAD: certification-sync `8828c96a99f6d3e0ca997530408184866a3d359a`

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
| P0.4 | Migration integrity | IMPLEMENTED — CI PENDING | Linear chain through 0018 audited; 0013 SQLite batch alteration; 0014 unique-link constraint; 0015 event time; 0016 ML lineage | Static chain regression added; runtime upgrade/downgrade not executed | c89e548 | PENDING | Fresh/upgrade/downgrade runtime verification still required |
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
| P1.15 | Auth/authorization | PARTIAL | Ownership-scoped APIs plus token validation; current code audit hardened password-change invalidation | Existing auth/ownership tests | — | Full endpoint matrix/runtime verification pending |
| P1.16 | Secrets/security | PARTIAL | Encrypted broker secrets, production JWT guard, sanitized Dhan errors/logs, live execution lock | Regression contracts | — | Deployment secret rotation/runtime verification pending |
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


### 2026-09-29 — Portfolio holding uniqueness hardening
- Found that portfolio holdings had no database uniqueness boundary for `(user_id, symbol)`, despite broker synchronization assuming one holding per symbol.
- Added `uq_holdings_user_symbol` as a unique database index.
- Manual holding creation now performs an ownership-scoped duplicate check and handles concurrent uniqueness races as a controlled conflict.
- Migration intentionally fails rather than silently consolidating pre-existing duplicate rows; any existing duplicates require explicit reconciliation before the migration can complete.
- Added regression coverage for the model/migration/service invariant.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Portfolio transaction rebuild concurrency hardening
- Found that transaction create/update/delete rebuilds all holdings for a user without a cross-worker serialization boundary.
- Added an ownership-scoped durable `users` row lock before transaction mutations/rebuilds, preventing concurrent workers from interleaving delete/rebuild/commit operations for the same user.
- Added a regression contract for the lock boundary.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-29 — Authentication/security hardening
- Added `password_changed_at` to users and migration 0018.
- Access and refresh tokens issued before a password change are rejected.
- Production configuration now refuses the known development JWT secret and defaults schema auto-creation off; deployment uses explicit migrations.
- Dhan provider error responses and retry logs no longer persist/print provider payloads or exception text.
- Added regression contracts for migration lineage, token invalidation and Dhan error sanitization.
- Status: IMPLEMENTED — CI PENDING.


## Latest signal-pipeline hardening — 2026-09-29
- Paper signal request completion now uses a row-level mutation lock and first-response-wins semantics.
- Crash-left pending signal recovery now covers both equity and option paper trades.
- Recovery is evidence-based and fail-closed: zero or multiple matching trades do not trigger creation/retry.
- Regression coverage added for repeated completion, exact equity recovery, and ambiguous equity recovery.


## Latest multi-worker hardening — 2026-09-29
- Removed process-global `_sessions`, `_market`, and `_restored` paper-state caches.
- Paper simulator state is reconstructed from durable DB state per request.
- Paper signal and market-bar mutation paths acquire a user-row lock.
- ML prediction persistence and market-state persistence support deferred commits so state can be committed with the durable session snapshot.
- Added regression contracts for request-scoped state and mutation serialization.
- PostgreSQL runtime concurrency behavior remains to be certified in an executable environment.


## Latest API/deployment hardening — 2026-09-29
- F&O position reads are now observational; quote-based paper marking uses an explicit POST mutation endpoint.
- F&O provider errors at the position-read boundary are sanitized.
- Docker deployment explicitly sets `TRADEPILOT_ENV=production`, activating production configuration guards.


## Latest transaction-boundary hardening — 2026-09-29
- Durable paper session state supports deferred commits.
- Signal completion supports deferred commits and is committed at the request boundary.
- Market-bar ML/learning/state writes can remain in the same transaction until request completion.
- Added regression contracts for the atomic mutation boundary.


## Latest paper transaction + UI hardening — 2026-09-29
- Authorization and revocation mutations now share the durable paper-state user lock with signal/market mutations, reducing authorization-vs-execution races.
- Paper signal request claiming supports deferred commit; the request claim, ML prediction, simulator state and terminal response can now share the request transaction.
- Dhan replay validation evidence no longer commits before persisted paper trades; successful replay evidence is committed after the complete durable mutation set is prepared.
- Added regression contracts for transaction boundaries.
- Frontend hardening added persistent hash navigation, workflow-stage navigation, shared UI primitives, improved accessibility semantics, isolated stock-search IDs, explicit paper-exit confirmation and F&O risk visibility.
- Status: IMPLEMENTED — CI / RUNTIME CERTIFICATION PENDING.


### 2026-09-30 — Backtest session-boundary audit
- Audited the existing next-bar-open backtest execution engine.
- Fixed a pending-signal/session-crossing defect: a signal generated in one NSE session is now discarded at the next session boundary.
- Intraday positions now flatten at the prior session close by default; overnight carry requires explicit `force_flat_at_session_end=False`.
- Added regression coverage for signal carry-over and session-end flattening.
- Added `docs/TRADEPILOT_BACKTEST_AUDIT.md` with remaining backtest gaps.
- Remaining: statutory India-equity fee model, entry-boundary dataset assertions, and broader malformed/duplicate/gap-risk regression coverage.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-30 — ML temporal tie handling
- ML events continue to order by event time plus persistence ID.
- Removed the incorrect global unique-timestamp requirement so simultaneous same-bar events can be evaluated deterministically.
- Backward event-time movement remains fail-closed.
- Added chronology regression coverage.
- Status: IMPLEMENTED — CI PENDING.

### 2026-09-30 — Paper reconciliation scope hardening
- Orphan learning-event detection now considers all Dhan paper trades, including still-open trades.
- Closed-trade reconciliation invariants remain strict for missing/broken links, symbol/session contamination, P&L mismatch and validation evidence.
- Added regression coverage for open-trade event scope.
- Status: IMPLEMENTED — CI PENDING.


### 2026-09-30 — Backtest input/fee hardening continuation
- Backtest input validation now fails closed on missing/invalid timestamps, duplicate or backward timestamps, mixed timezone awareness, malformed OHLC values, and mixed symbols.
- Integrated the explicit India-equity fee schedule into actual backtest cash/P&L accounting; entry and exit fee breakdowns are persisted in trade evidence.
- Added regression coverage for duplicate/backward timestamps, symbol mixing, malformed OHLC, fee integration, gap-through-stop behavior, same-bar stop/target ordering, and daily-loss halting.
- The configured fee schedule is versioned and surfaced in the result. Historical research must select a schedule appropriate to the data period; no historical statutory rates are inferred.
- Status: IMPLEMENTED — CI PENDING.

### 2026-09-30 — Deployment/CI hardening continuation
- CI now triggers on `certification-sync` pushes as well as main/feature branches.
- Production backend Docker image is aligned to Python 3.12, matching CI.
- Production Compose now requires explicit PostgreSQL password and CORS configuration, adds backend readiness health checks, and waits for backend readiness before starting the frontend.
- Added `docs/TRADEPILOT_PRODUCTION_READINESS.md` covering backup/restore and environment-dependent runtime drills.
- Status: IMPLEMENTED — runtime deployment verification remains pending.


### 2026-09-30 — Current-head CI certification
- GitHub Actions run **1646** for commit `f7fd9af8848087014f7aab29e8e2f6a4f5b5fda9` completed successfully.
- Backend: 835 passed, 1 skipped, 102 warnings; compile and fresh Alembic migration passed.
- Frontend production build passed.
- Docker Compose deployment-config validation passed.
- Release gate passed.
- Earlier failed CI iterations exposed and fixed: explicit CORS CI environment, legacy brokerage compatibility, optional legacy open field, and the ML duplicate-timestamp test contract.
- Status: **DONE — current-head CI verified**.


### 2026-09-30 — Final current-head CI verification (run 1649)
- PR #46 current head is `70a1ee5fbbbd9bd1a31c461c84a430dd30471985` on `certification-sync`.
- GitHub Actions run **1649** (`36755021474`) completed successfully for that exact SHA.
- Backend, frontend, deployment-config, and release-gate jobs all passed; backend reported 835 passed, 1 skipped, 102 warnings.
- Engineering audit found no fee double-counting in cash accounting: entry/exit fees are deducted once from cash, while trade P&L uses the same fee evidence for reporting only.
- Legacy brokerage-rate compatibility, session-boundary behavior, walk-forward boundaries, equal ML event timestamps, and open-trade reconciliation scope remain covered by regression tests.
- Live execution remains LOCKED. Corporate-action state remains UNKNOWN. Production runtime drills remain environment-dependent.
- Status: **DONE — current-head engineering CI verified; research/production certification blockers remain.**


### 2026-09-30 — Research certification gate hardening
- Added a shared fail-closed research dataset gate requiring persisted provenance, VALID quality status, matching SHA-256 content fingerprint, and explicit corporate-action adjustment state for performance research.
- Stored intraday backtests now require this certification boundary before analytics execute.
- Research API performance, walk-forward, experiment, research-lab, and regime analytics now use the certification boundary; data-quality inspection remains available separately so uncertified datasets can still be diagnosed.
- Added regression coverage for missing provenance, fingerprint mismatch, unknown corporate-action state, and successful explicit-state certification.
- Status: IMPLEMENTED — CI pending on current head; real-data qualification remains blocked until source-backed corporate-action state is available.



### 2026-10-01 — Real intraday dataset quarantine and certification hardening
- Audited the supplied local SQLite intraday dataset covering roughly 2021-08 through 2026-08.
- Confirmed structural defects in the supplied audit: negative volume rows, weekend bars during NSE equity market hours, and synchronized large price discontinuities requiring source/corporate-action review.
- Preserved the raw dataset as forensic input; no rows were silently corrected or deleted.
- Research certification now independently rejects weekend bars, bars outside the regular NSE equity session, negative volume, and mixed source timezone offsets before analytics can consume the dataset.
- Added regression coverage for weekend, negative-volume, and outside-session certification failures.
- Large price moves remain a diagnostic/manual-review signal rather than an automatic rejection, because genuine corporate actions can create large discontinuities.
- Status: IMPLEMENTED — current-head CI pending; supplied real dataset remains NOT CERTIFIED until rebuilt/revalidated with source-backed session/calendar and corporate-action evidence.


### 2026-10-01 — Research analytics bypass audit
- Audited remaining intraday research routes after the shared certification gate was introduced.
- Batch research now enforces certification inside the batch service itself rather than relying only on an API pre-check.
- Scorecard and evidence aggregation now load requested datasets through the certified dataset helper.
- This closes the identified API/service paths that could otherwise consume stored bars without provenance, structural-data, and corporate-action certification.
- Status: IMPLEMENTED — current-head CI result still not observable.


### 2026-10-01 — Portfolio risk consistency hardening
- Audited the separate portfolio-risk layer without modifying the completed research-certification work.
- Found that invalid existing portfolio positions with negative market value or negative stop-loss risk were silently clamped to zero instead of failing closed.
- Added strict validation for existing positions and portfolio risk configuration bounds.
- Added regression coverage for invalid exposure, invalid risk, and invalid configuration.
- Status: IMPLEMENTED — current-head CI pending.


### 2026-10-01 — Execution and operational boundary hardening
- Hardened execution idempotency ordering: an explicit idempotency key is consumed only after every authorization/validation gate succeeds, so a rejected intent can be safely retried with the same key.
- Added regression coverage for retry-after-rejection and duplicate-after-success behavior.
- Hardened operational audit-event reads to scope results to the authenticated user; cross-user audit records are no longer exposed by the operations API.
- No change to the research-certification/data-quality workstream.
- Status: IMPLEMENTED — CI PENDING.


### 2026-10-01 — Authentication debug-surface hardening
- Password-reset debug-token output is now forcibly disabled when `TRADEPILOT_ENV` is production/prod, even if the debug environment variable is accidentally enabled.
- Live execution remains hard-disabled.
- Status: IMPLEMENTED — CI PENDING.


### 2026-10-01 — Deployment verification automation
- CI now provisions PostgreSQL 16 and runs Alembic upgrade/downgrade/re-upgrade against a real PostgreSQL service.
- Added a guarded PostgreSQL custom-format backup/restore drill script. It refuses source-to-source restoration and requires explicit `CONFIRM_RESTORE=YES` plus a dedicated restore target.
- These changes make PostgreSQL migration and recovery verification executable; an actual production backup/restore drill still requires a deployed environment.
- Status: IMPLEMENTED — CI PENDING.


### 2026-10-01 — CI failure remediation
- Investigated GitHub Actions run 1713: frontend, Docker Compose validation, and PostgreSQL migration verification passed; backend failed 7 tests.
- Root causes were test fixtures/helpers not aligned with the stricter certification contract, plus fingerprint instability between integer/float representations after normalization.
- Canonicalized dataset fingerprint numeric fields and updated structural-gate fixtures without weakening production certification rules.
- Status: FIXED — CI verification in progress.


### 2026-10-01 — CI restored green
- Latest GitHub Actions run 1725 for the corrected head passed all jobs: backend, frontend, PostgreSQL migrations, deployment-config, and release-gate.
- Backend result: 850 passed, 1 skipped, with existing warnings only.
- Root causes of the prior seven backend failures were corrected without weakening research certification: canonical fingerprint numeric normalization, raw structural-defect fixture coverage, certified batch-store fixtures, explicit Asia/Kolkata batch timestamps, and correct missing-dataset handling.
- Current CI status: GREEN.


### 2026-10-01 — Current-head CI and NSE session-calendar verification
- GitHub Actions run **1746** completed successfully for current HEAD `8828c96a99f6d3e0ca997530408184866a3d359a`.
- Current-head CI is green across backend, frontend, PostgreSQL migrations, deployment-config, and release-gate jobs.
- Source-backed NSE exceptional-session classification is now integrated into research certification. Documented Muhurat/special sessions are treated by explicit windows; documented mock sessions remain non-researchable; unknown weekend sessions fail closed.
- Real-data structural rerun against the supplied `equity_nse_discovery_5m` dataset found **0 unknown weekend rows** and **0 bars outside all known session windows** after resolving the documented 2022-10-24 and 2024-11-01 Muhurat sessions.
- The dataset remains **NOT CERTIFIED** because 18 negative-volume rows remain and corporate-action adjustment provenance is still not established. Raw data was not repaired or deleted.
- Strict 5-minute certification remains separate and is not weakened by the calendar work.
- Status: DONE — implementation and current-head CI verification complete; real-data certification remains blocked by data/provenance evidence.
