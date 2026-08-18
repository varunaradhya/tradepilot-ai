# TradePilot AI — Feature & Development Register

**Purpose:** Single source of truth for implemented, in-progress, planned and intentionally locked TradePilot capabilities.

**Repository:** `varunaradhya/tradepilot-ai`  
**Last audited:** 2026-08-18  
**Status:** Active

## Current P1 implementation

| Priority | Feature | Status |
|---|---|---|
| P1 | Paper monitoring/alerting foundation | IMPLEMENTED |
| P1 | Read-only paper health endpoint | IMPLEMENTED |
| P1 | Paper state/ledger reconciliation halt gate | IMPLEMENTED |
| P1 | Simulation-only operational monitoring | IMPLEMENTED |
| P1 | Deterministic/order-independent reconciliation | IMPLEMENTED |
| P1 | Fail-closed invalid reconciliation data handling | IMPLEMENTED |
| P1 | Minimum paper-evidence monitoring warning | IMPLEMENTED |
| P1 | Production market-data scheduler | ENVIRONMENTAL |
| P1 | Strategy research dashboard | EXISTING / EXTEND |
| P1 | Parameter sensitivity visualization | EXISTING / EXTEND |
| P1 | Regime-performance dashboard | EXISTING / EXTEND |

P1 monitoring is deliberately read-only and cannot place, modify or cancel broker orders. Reconciliation failures surface `HALT_AND_RECONCILE` rather than silently repairing state. Reconciliation is independent of database retrieval order and invalid trade data fails closed.

## Permanent constraints

1. India/NSE first.
2. Intraday first.
3. Paper first.
4. Risk before execution.
5. Evidence before promotion.
6. Never optimize against OOS data.
7. Never use future information in signal/backtest calculations.
8. Live execution remains locked.

## Agile lifecycle

### Phase 2 — Paper-market validation
**Status: NEXT / ACTIVE**

Required:
- reliable market-data runtime
- NSE session handling
- immutable signal capture
- complete paper trade lifecycle
- realistic simulated execution
- order/position/exit reconciliation
- net P&L reconciliation
- backtest-vs-paper divergence analysis
- adversarial paper-trading QA

### Phase 3 — Strategy readiness
**Status: EVIDENCE GATED**

Historical evidence and paper evidence must pass their respective gates before promotion.

### Phase 4 — Live execution
**Status: LOCKED**

Live order placement remains disabled until production safeguards, broker integration validation, paper-performance gates, operational monitoring and explicit owner approval are satisfied.

## Definition of Done

- Existing implementation checked; no duplicate production engine created.
- Backend/domain logic implemented.
- API/schema changes implemented where required.
- Automated regression coverage added.
- Backend CI green.
- Frontend build green where affected.
- Documentation updated.
- Trading features remain simulation-only unless separately reviewed and unlocked.
- Failure modes are tested and fail safely.

## Latest engineering focus

P1 stabilization is tightening the paper monitoring boundary before Phase 2. The canonical monitoring service owns operational health snapshots; reconciliation is deterministic and fail-closed. Phase 2 must extend evidence collection rather than bypassing the paper gate.
