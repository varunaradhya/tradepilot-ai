# TradePilot AI — Engineering Ledger

Repository: varunaradhya/tradepilot-ai
Branch: main
Last updated: 2026-09-29
Current HEAD: 78068372e17eb112761c28b42f47612b091cf35f

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
| P0.4 | Migration integrity | IMPLEMENTED — CI PENDING | Linear 001→014 chain audited; 0013 SQLite batch alteration; 0014 unique-link constraint | Static chain regression added; runtime upgrade/downgrade not executed | c89e548 | PENDING | Fresh/upgrade/downgrade runtime verification still required |
| P1.1 | Historical ingestion hardening | PARTIAL | Dhan path normalized + session-aware; portable import now reuses canonical contract | Import/provenance regression tests added; CI pending | 2fb579e | PENDING | Corporate-action treatment and runtime evidence remain |
| P1.2 | Backtest audit | IMPLEMENTED — CI PENDING | Same-bar execution leakage fixed; signals execute next-bar open; dataset fingerprint propagated | Regression coverage added | 46cf600 | PENDING | Future-high/low, normalization, overlap and runtime evidence remain |
| P1.3 | Walk-forward validation audit | PARTIAL — CI PENDING | Chronological non-overlapping windows plus dataset fingerprint lineage | Regression coverage added | abb9483 | Runtime/OOS evidence remains |
| P1.4 | Strategy framework audit | PLANNED | V1/V2/V2A registry exists | Existing tests | — | — | Parameter provenance/fingerprinting pending |
| P1.5 | ML data integrity | IMPLEMENTED — CI PENDING | Temporal feature-event timestamp persisted and required | Existing ML service | Existing tests | — | — | Feature/label schema audit pending |
| P1.6 | ML leakage protection | PARTIAL — CI PENDING | Temporal event ordering hardened; test set removed from qualification gate | Regression coverage added | ed45f12 | PENDING | Broader research leakage suite remains |
| P1.7 | ML lifecycle | PARTIAL | Training/deployment gates exist | Existing tests | — | PENDING | Rollback/version lifecycle audit pending |
| P1.8 | ML evaluation | IMPLEMENTED — CI PENDING | Classification + trade-level P&L/R-multiple metrics added | Regression coverage added | b47c420 | PENDING | Calibration/real-data evidence remains |
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
