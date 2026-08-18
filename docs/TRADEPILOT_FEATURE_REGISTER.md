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

## P5 — Production reliability & broker sandbox

| Capability | Status |
|---|---|
| Durable database-backed kill switch | IMPLEMENTED |
| Fail-safe kill switch defaults to active | IMPLEMENTED |
| Application-level kill-switch activation endpoint | IMPLEMENTED |
| Kill-switch deactivation via trading API | INTENTIONALLY NOT PROVIDED |
| Market-data freshness watchdog with future/stale timestamp rejection | IMPLEMENTED |
| Operational safety endpoint uses persisted market-data health | IMPLEMENTED |
| Operational safety endpoint uses persisted paper reconciliation health | IMPLEMENTED |
| Operational audit-event persistence | IMPLEMENTED |
| Bounded recent audit-event API | IMPLEMENTED |
| Configurable audit-event retention service | IMPLEMENTED |
| Read-only broker sandbox certification contract | IMPLEMENTED |
| Dhan/Groww/Angel One live-order capability remains blocked | LOCKED |
| Production observability/SLO deployment | IMPLEMENTED |
| Sandbox credential readiness without secret exposure | IMPLEMENTED |
| Real broker sandbox credentials/certification | ENVIRONMENTAL |
| Live execution | LOCKED |

## P6 — Production observability

| Capability | Status |
|---|---|
| Bounded request telemetry | IMPLEMENTED |
| Error-rate and latency SLO snapshot | IMPLEMENTED |
| Database dependency health | IMPLEMENTED |
| Market-data freshness health | IMPLEMENTED |
| Kill-switch operational visibility | IMPLEMENTED |
| Secret-safe sandbox credential readiness | IMPLEMENTED |
| P6 observability regression coverage | IMPLEMENTED |
| External metrics/alert delivery | ENVIRONMENTAL |

## P7 — Final validation & attack phase

| Capability | Status |
|---|---|
| Registered-broker live-execution safety regression gates | IMPLEMENTED |
| Sandbox certification never authorizes live execution | IMPLEMENTED |
| Unknown broker fail-closed certification test | IMPLEMENTED |
| Broker capability contract live-order gate | IMPLEMENTED |
| Full P1–P6 regression suite | CI REQUIRED |
| Backend compile/tests | CI REQUIRED |
| Frontend production build | CI REQUIRED |
| Docker Compose deployment validation | CI REQUIRED |
| Real provider sandbox connectivity | ENVIRONMENTAL |
| Production monitoring/alerts | ENVIRONMENTAL |
| Independent live-execution safety review | BLOCKING |
| Live execution | LOCKED |

**P7 safety boundary:** P7 is a validation/attack phase. It does not add real-money execution or remove any existing safety gate.

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
**Status: IMPLEMENTED — LIVE EXECUTION LOCKED**

P4 establishes the central safety boundary and operational status contract.

### Phase 5 — Production reliability & broker sandbox
**Status: IMPLEMENTED — ENVIRONMENTAL ITEMS REMAIN**

P5 establishes durable kill-switch state, fail-closed market-data watchdog logic, operational audit retention, runtime safety visibility and read-only broker sandbox certification.

### Phase 6 — Production observability
**Status: IMPLEMENTED — DEPLOYMENT ITEMS REMAIN**

P6 adds bounded request telemetry, SLO health reporting, dependency visibility and secret-safe sandbox credential readiness. Live execution remains locked.

### Phase 7 — Final validation / attack phase
**Status: IMPLEMENTED — CI AND ENVIRONMENTAL GATES REMAIN**

P7 hardens the existing safety boundary with broker capability regression tests and documents the final attack matrix. CI must prove backend tests, frontend build and deployment configuration before the system can be considered release-ready.

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
- A missing CI run is not treated as a passing CI run.

## Latest engineering focus

P7 final validation is now the active engineering milestone. The application-level trading foundation is complete through P7, while real broker sandbox connectivity, deployment observability and independent live-execution review remain environmental/blocking gates. Live execution remains locked.
