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
| P1 | Regime-performance visualization | EXISTING / EXTEND |

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
| Production continuous scheduler | ENVIRONMENTAL |

**P2 safety boundary:** all execution remains `SIMULATION_ONLY`; broker orders are disabled. Divergence evidence is diagnostic and can never authorize live trading.

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

**P3 safety boundary:** `READY_FOR_STRATEGY_REVIEW` is an evidence result, not permission to place live orders. `live_trading_allowed` remains permanently false in this phase.

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

### Phase 1 — Research / historical validation
**Status: EXISTING FOUNDATION**

Research data, intraday strategy, backtesting, robustness and walk-forward qualification already exist and remain evidence-gated.

### Phase 2 — Paper-market validation
**Status: IMPLEMENTED — CI GATE**

P2 covers the end-to-end simulation boundary: qualified signal capture → risk checks → simulated execution → position lifecycle → net P&L → persistence/reconciliation → evidence comparison.

### Phase 3 — Strategy readiness
**Status: IMPLEMENTED — EVIDENCE GATED**

A strategy must pass historical qualification, cross-stock consistency, sustained paper performance, statistical confidence, regime stability, bounded drawdown/loss streaks, parameter-fingerprint stability, divergence limits and evidence freshness before it can reach `READY_FOR_STRATEGY_REVIEW`.

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

P3 hardens the promotion boundary rather than adding execution power. The next phase should attack production operationalization: reliable market-data runtime, evidence persistence/retention, monitoring SLAs, deployment configuration and only then a separately reviewed live-broker safety architecture.
