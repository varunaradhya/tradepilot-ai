# TradePilot AI — Feature & Development Register

**Purpose:** Single source of truth for implemented, in-progress, planned and intentionally locked TradePilot capabilities.

**Repository:** `varunaradhya/tradepilot-ai`
**Last audited:** 2026-08-18
**Status:** Active

## P1–P8 status

P1 Paper Operations — IMPLEMENTED  
P2 Intraday Paper Validation — IMPLEMENTED  
P3 Strategy Readiness — IMPLEMENTED / EVIDENCE GATED  
P4 Production Safety — IMPLEMENTED / LIVE LOCKED  
P5 Production Reliability & Broker Sandbox — IMPLEMENTED / ENVIRONMENTAL ITEMS REMAIN  
P6 Production Observability — IMPLEMENTED / EXTERNAL DELIVERY REMAINS ENVIRONMENTAL  
P7 Final Validation & Attack Phase — IMPLEMENTED / CI AND ENVIRONMENTAL GATES REMAIN  
P8 Release & Production Readiness — IMPLEMENTED / CI VALIDATED

## P9 — Final Production Validation

| Capability | Status |
|---|---|
| CI/backend/frontend/deployment release gate | IMPLEMENTED / CI VALIDATED |
| Trading safety regression gate | IMPLEMENTED |
| Strategy evidence gate definition | IMPLEMENTED / EVIDENCE-GATED |
| Operational failure-injection matrix | IMPLEMENTED / TEST-GATED |
| Security gate definition | IMPLEMENTED / DEPLOYMENT-GATED |
| Final production validation runbook | IMPLEMENTED |
| Real broker sandbox credentials/certification | ENVIRONMENTAL / BLOCKING |
| External monitoring/alert delivery | ENVIRONMENTAL / BLOCKING |
| Production backup/restore drill | ENVIRONMENTAL / BLOCKING |
| TLS/network/deployment verification | ENVIRONMENTAL / BLOCKING |
| Independent live-order safety review | BLOCKING |
| Live execution | LOCKED |

## Permanent constraints

1. India/NSE first.
2. Intraday first.
3. Paper first.
4. Risk before execution.
5. Evidence before promotion.
6. Never optimize against OOS data.
7. Never use future information in signal/backtest calculations.
8. Never treat missing CI evidence as a pass.
9. Live execution remains locked until independent review and explicit approval.

## Agile lifecycle

```text
RESEARCH
  ↓
DATA VALIDATION
  ↓
BACKTEST
  ↓
ROBUSTNESS
  ↓
WALK-FORWARD
  ↓
OUT-OF-SAMPLE
  ↓
STRATEGY QUALIFICATION
  ↓
PAPER TRADING
  ↓
PAPER PERFORMANCE GATE
  ↓
READINESS REVIEW
  ↓
PRODUCTION SAFETY
  ↓
RELIABILITY + OBSERVABILITY
  ↓
CI/CD RELEASE GATE
  ↓
FINAL PRODUCTION VALIDATION (P9)
  ↓
EXTERNAL SANDBOX / DEPLOYMENT GATES
  ↓
INDEPENDENT LIVE-ORDER SAFETY REVIEW
  ↓
EXPLICIT USER APPROVAL
  ↓
LIVE TRADING (NOT ENABLED)
```

## Definition of Done

- Existing implementation checked; no duplicate production engine created.
- Automated regression coverage added where applicable.
- Backend CI green.
- Frontend build green where affected.
- Docker/deployment validation green.
- Documentation updated.
- Failure modes are tested and fail safely.
- Environmental gates are explicitly identified rather than fabricated.
- Trading remains simulation-only unless separately reviewed and unlocked.

## Source of truth rule

Before adding a subsystem, inspect this register and the existing implementation. Update this document whenever a feature changes state.
