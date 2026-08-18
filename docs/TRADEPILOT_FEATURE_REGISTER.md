# TradePilot AI — Feature & Development Register

**Purpose:** Single source of truth for implemented, in-progress, planned and intentionally locked TradePilot capabilities.

**Repository:** `varunaradhya/tradepilot-ai`  
**Last audited:** 2026-08-18  
**Status:** Active

## P1 — Paper operations

| Capability | Status |
|---|---|
| Paper monitoring/alerting foundation | IMPLEMENTED |
| Read-only paper health endpoint | IMPLEMENTED |
| Paper state/ledger reconciliation halt gate | IMPLEMENTED |
| Simulation-only operational monitoring | IMPLEMENTED |
| Deterministic/order-independent reconciliation | IMPLEMENTED |
| Fail-closed invalid reconciliation data handling | IMPLEMENTED |
| Minimum paper-evidence monitoring warning | IMPLEMENTED |
| Production market-data scheduler | ENVIRONMENTAL |

## P2 — Intraday paper-market validation

| Capability | Status |
|---|---|
| NSE/IST session-aware paper lifecycle | IMPLEMENTED |
| Server-controlled strategy qualification gate | IMPLEMENTED |
| Immutable/idempotent signal request capture | IMPLEMENTED |
| Signal → paper position lifecycle | IMPLEMENTED |
| Risk-based position sizing | IMPLEMENTED |
| Stop/target/trailing-stop/time exits | IMPLEMENTED |
| Session-close position handling | IMPLEMENTED |
| Realistic Indian transaction-cost simulation | IMPLEMENTED |
| Net paper P&L | IMPLEMENTED |
| Paper state persistence and restoration | IMPLEMENTED |
| Paper monitoring + reconciliation | IMPLEMENTED |
| Backtest-vs-paper divergence evidence | IMPLEMENTED |
| Paper evidence API | IMPLEMENTED |
| Adversarial regression coverage | IMPLEMENTED |

**P2 safety boundary:** all execution remains `SIMULATION_ONLY`; broker orders are disabled.

## P3 — Strategy readiness

| Capability | Status |
|---|---|
| Minimum sustained paper-trade sample | IMPLEMENTED |
| Paper profit-factor gate | IMPLEMENTED |
| Paper drawdown ceiling | IMPLEMENTED |
| Maximum consecutive-loss gate | IMPLEMENTED |
| Average-R quality gate | IMPLEMENTED |
| Statistical lower-confidence bound | IMPLEMENTED |
| Chronological regime-window stability | IMPLEMENTED |
| Backtest-vs-paper return/drawdown divergence gate | IMPLEMENTED |
| Strategy fingerprint / parameter-drift gate | IMPLEMENTED |
| Evidence freshness gate | IMPLEMENTED |
| Fail-closed strategy readiness API | IMPLEMENTED |
| Adversarial P3 regression coverage | IMPLEMENTED |
| Live execution promotion | LOCKED |

## P4 — Production safety foundation

| Capability | Status |
|---|---|
| Central fail-closed execution safety policy | IMPLEMENTED |
| Explicit `SIMULATION_ONLY` execution mode | IMPLEMENTED |
| Permanent live-order block at safety layer | IMPLEMENTED |
| Kill-switch-aware paper-operation gate | IMPLEMENTED |
| Market-data freshness gate contract | IMPLEMENTED |
| Reconciliation-health gate contract | IMPLEMENTED |
| Read-only production safety status endpoint | IMPLEMENTED |
| NSE session status included in operational status | IMPLEMENTED |
| P4 adversarial safety regression coverage | IMPLEMENTED |
| Production broker live-order enablement | LOCKED |
| Automatic live-order promotion | LOCKED |
| Production deployment/runtime SLOs | NEXT / ENVIRONMENTAL |
| Durable multi-instance kill switch | NEXT |
| Evidence retention/observability pipeline | NEXT |

**P4 safety boundary:** no environment variable or broker connection can make live order execution available through this milestone. Live order authorization remains explicitly blocked in code. Paper operations require fresh market data, healthy reconciliation and an inactive kill switch.

## Permanent constraints

1. India/NSE first.
2. Intraday first.
3. Paper first.
4. Risk before execution.
5. Evidence before promotion.
6. Never optimize against OOS data.
7. Never use future information in signal/backtest calculations.
8. Live execution remains locked until a separate safety review.

## Agile lifecycle

### Phase 1 — Research / historical validation
**Status: EXISTING FOUNDATION**

Research data, intraday strategy, backtesting, robustness and walk-forward qualification exist and remain evidence-gated.

### Phase 2 — Paper-market validation
**Status: IMPLEMENTED — CI GATE**

Qualified signal capture → risk checks → simulated execution → position lifecycle → net P&L → persistence/reconciliation → evidence comparison.

### Phase 3 — Strategy readiness
**Status: IMPLEMENTED — EVIDENCE GATED**

Historical qualification, cross-stock consistency, sustained paper performance, statistical confidence, regime stability, bounded drawdown/loss streaks, fingerprint stability, divergence limits and evidence freshness are required.

### Phase 4 — Production safety
**Status: FOUNDATION IMPLEMENTED — LIVE EXECUTION LOCKED**

P4 establishes the central safety boundary and operational status contract. The remaining production work is environmental and operational: durable state, observability, deployment SLOs, broker sandbox validation and independent live-execution review.

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

P4 establishes the fail-closed production safety boundary. The next move is operational hardening rather than live trading: durable kill-switch state, market-data watchdogs, evidence/audit retention, deployment SLOs and broker sandbox certification.
