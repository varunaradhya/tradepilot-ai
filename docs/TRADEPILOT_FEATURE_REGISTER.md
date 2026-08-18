# TradePilot AI — Feature & Development Register

**Purpose:** Single source of truth for implemented, in-progress, planned and intentionally locked TradePilot capabilities.

**Repository:** `varunaradhya/tradepilot-ai`  
**Last audited:** 2026-08-18  
**Status:** Active

## P1–P7 status

P1 Paper Operations — IMPLEMENTED  
P2 Intraday Paper Validation — IMPLEMENTED  
P3 Strategy Readiness — IMPLEMENTED / EVIDENCE GATED  
P4 Production Safety — IMPLEMENTED / LIVE LOCKED  
P5 Production Reliability & Broker Sandbox — IMPLEMENTED / ENVIRONMENTAL ITEMS REMAIN  
P6 Production Observability — IMPLEMENTED / EXTERNAL DELIVERY REMAINS ENVIRONMENTAL  
P7 Final Validation & Attack Phase — IMPLEMENTED / CI AND ENVIRONMENTAL GATES REMAIN

## P8 — Release & Production Readiness

| Capability | Status |
|---|---|
| Explicit GitHub Actions workflow trigger | IMPLEMENTED |
| Manual CI workflow dispatch | IMPLEMENTED |
| Least-privilege CI token permissions | IMPLEMENTED |
| CI concurrency/cancel stale runs | IMPLEMENTED |
| Backend dependency caching | IMPLEMENTED |
| Backend compile gate | IMPLEMENTED |
| Backend test gate | IMPLEMENTED |
| Frontend production build gate | IMPLEMENTED |
| Docker Compose deployment gate | IMPLEMENTED |
| Explicit fail-closed release gate | IMPLEMENTED |
| CI timeouts | IMPLEMENTED |
| Release/deployment runbook | IMPLEMENTED |
| Post-deployment health/readiness verification | DOCUMENTED |
| External metrics/alerts | ENVIRONMENTAL |
| Real broker sandbox credentials/certification | ENVIRONMENTAL |
| Production backup/restore validation | ENVIRONMENTAL |
| Independent live-execution safety review | BLOCKING |
| Live execution | LOCKED |

## P8 release boundary

A missing CI workflow run is not considered a pass. All required CI jobs and the final release gate must succeed before a release is considered technically validated.

P8 does **not** enable real-money execution. Broker sandbox certification cannot authorize live orders. The system remains `SIMULATION_ONLY` until a separate future safety review explicitly changes that policy.

## Permanent constraints

1. India/NSE first.
2. Intraday first.
3. Paper first.
4. Risk before execution.
5. Evidence before promotion.
6. Never optimize against OOS data.
7. Never use future information in signal/backtest calculations.
8. Live execution remains locked until a separate safety review and explicit approval.

## Definition of Done

- Existing implementation checked; no duplicate production engine created.
- Backend/domain logic implemented.
- API/schema changes implemented where required.
- Automated regression coverage added.
- Backend CI green.
- Frontend build green where affected.
- Deployment configuration validated.
- Documentation updated.
- Trading features remain simulation-only unless separately reviewed and unlocked.
- Failure modes are tested and fail safely.
- Missing CI evidence blocks release.

## Current milestone

**P8 — Release & Production Readiness: IMPLEMENTED in code/documentation.**

Remaining release blockers are environmental: actual GitHub Actions execution, real provider sandbox credentials/certification, external monitoring/alerts, backup/restore validation and independent live-execution safety review.
