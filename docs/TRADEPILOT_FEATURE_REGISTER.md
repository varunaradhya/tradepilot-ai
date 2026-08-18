# TradePilot AI — Feature & Development Register

**Purpose:** Single source of truth for implemented, in-progress, planned and intentionally locked TradePilot capabilities.

**Repository:** `varunaradhya/tradepilot-ai`  
**Last audited:** 2026-08-18  
**Status:** Active

## How this document is used

Before coding:
1. Read this register.
2. Locate the existing implementation and tests.
3. Extend existing functionality instead of creating duplicates.
4. Add genuinely new work to the backlog before implementation.

After coding:
1. Test the change.
2. Run CI/build verification.
3. Update this register in the same change/PR.
4. Only mark a feature IMPLEMENTED after verification.

This document is the **project-memory/index layer**. Detailed technical documents remain authoritative for their specific subjects.

---

# 1. Product vision

TradePilot AI is a risk-first Indian-market stock research, strategy-validation and paper-trading platform focused first on **intraday equity trading**.

```text
Indian market data
    ↓
Data quality validation
    ↓
Opportunity scanner
    ↓
Strategy signal
    ↓
Signal evidence / explanation
    ↓
Historical qualification
    ↓
Position sizing + risk controls
    ↓
Paper execution
    ↓
Paper performance evidence
    ↓
Readiness review
    ↓
Future controlled live review
```

**Safety boundary:** real-money order execution remains intentionally locked. Historical/backtest performance is research evidence, not a guarantee of future performance.

---

# 2. Current implementation inventory

## 2.1 Strategy and quantitative research

| Capability | Status |
|---|---|
| Deterministic long-first intraday signal engine | IMPLEMENTED |
| Opening Range Breakout strategy | IMPLEMENTED |
| 9/20 EMA trend alignment | IMPLEMENTED |
| Relative-volume confirmation | IMPLEMENTED |
| ATR stop/target | IMPLEMENTED |
| Opening-gap rejection | IMPLEMENTED |
| Risk-based position sizing | IMPLEMENTED |
| Maximum capital allocation | IMPLEMENTED |
| No overnight carry in intraday backtest | IMPLEMENTED |
| Historical backtesting | IMPLEMENTED |
| Walk-forward validation | IMPLEMENTED |
| Robustness/stress analysis | IMPLEMENTED |
| Multi-stock historical validation | IMPLEMENTED |
| Strategy qualification | IMPLEMENTED |
| Strategy readiness | IMPLEMENTED / EVIDENCE GATED |
| Strategy-version-scoped evidence | IMPLEMENTED |
| Strategy quality/regime analysis | IMPLEMENTED |
| ORB momentum strategy family | IMPLEMENTED (`ORB_MOMENTUM_V1`) |
| VWAP mean-reversion strategy family | IMPLEMENTED (`VWAP_MEAN_REVERSION_V2`) |
| Equity strategy comparison lab | IMPLEMENTED |
| Indian-market research pipeline | IMPLEMENTED |
| F&O V1 research protocol | IMPLEMENTED AS RESEARCH PROTOCOL ONLY |

**Important:** Do not create another first strategy unless evidence shows the existing research family is insufficient. Primary intraday strategy details live in `docs/intraday-strategy.md`.

## 2.2 Market data and Indian-market discovery

| Capability | Status |
|---|---|
| Market-provider abstraction | IMPLEMENTED |
| Historical market-data services | IMPLEMENTED |
| Research data cache | IMPLEMENTED |
| NSE instrument master/security mapping | IMPLEMENTED |
| Indian/NSE-first stock search | IMPLEMENTED |
| Server-side Indian equity validation | IMPLEMENTED |
| Multi-stock opportunity scanner | IMPLEMENTED |
| Signal-to-trade-decision composition | IMPLEMENTED |
| Session-aware market-data handling | IMPLEMENTED |
| Intraday candle validation: duplicate/missing/stale/out-of-order | IMPLEMENTED |
| Continuous production market-data scheduler | ENVIRONMENTAL |

## 2.3 Signal/decision layer

| Capability | Status |
|---|---|
| Deterministic signal engine | IMPLEMENTED |
| Long-first BUY architecture | IMPLEMENTED |
| Neutral/no-trade outcome | IMPLEMENTED |
| Signal evidence/explanation | IMPLEMENTED |
| Signal → paper decision workflow | IMPLEMENTED |
| Risk/reward validation | IMPLEMENTED |
| Position sizing | IMPLEMENTED |
| Strategy readiness gate | IMPLEMENTED |
| Central execution safety gate | IMPLEMENTED |
| Duplicate-signal protection | IMPLEMENTED |

## 2.4 Risk and execution safety

| Capability | Status |
|---|---|
| Position sizing/risk budget | IMPLEMENTED |
| Maximum capital/order-value controls | IMPLEMENTED |
| Daily risk budget | IMPLEMENTED |
| Daily loss limit | IMPLEMENTED |
| Trade-count limit | IMPLEMENTED |
| Loss-streak protection | IMPLEMENTED |
| Open-position limit | IMPLEMENTED |
| Risk/reward validation | IMPLEMENTED |
| Long-only intraday policy | IMPLEMENTED |
| Execution safety gate | IMPLEMENTED |
| LIVE execution lock | IMPLEMENTED / LOCKED |
| Paper input validation: finite prices/configuration | IMPLEMENTED |
| Paper OHLC integrity validation | IMPLEMENTED |
| Paper session monotonicity protection | IMPLEMENTED |
| Symbol-isolated paper state | IMPLEMENTED |

## 2.5 Paper trading

| Capability | Status |
|---|---|
| Simulation-only paper engine | IMPLEMENTED |
| Long-first paper orchestrator | IMPLEMENTED |
| Paper session lifecycle | IMPLEMENTED |
| Paper market-bar ingestion | IMPLEMENTED |
| Persistent paper trades/ledger | IMPLEMENTED |
| Paper cockpit | IMPLEMENTED |
| Paper performance aggregation | IMPLEMENTED |
| Paper evidence metrics | IMPLEMENTED |
| Paper risk-quality readiness gate | IMPLEMENTED |
| Paper readiness gate | IMPLEMENTED |
| Signal → risk → paper order → position → exit | IMPLEMENTED |
| Net P&L including realistic costs | IMPLEMENTED |
| Slippage/market-impact modelling | IMPLEMENTED |
| Gap-through-stop/target handling | IMPLEMENTED |

## 2.6 Performance/evidence

| Capability | Status |
|---|---|
| Win rate | IMPLEMENTED |
| Profit factor | IMPLEMENTED |
| Expectancy | IMPLEMENTED |
| Drawdown | IMPLEMENTED |
| Trade count | IMPLEMENTED |
| Multi-stock aggregation | IMPLEMENTED |
| Strategy-version evidence | IMPLEMENTED |
| Historical evidence | IMPLEMENTED |
| Paper evidence | IMPLEMENTED |
| Historical + paper readiness workflow | IMPLEMENTED |
| Robustness evidence | IMPLEMENTED |
| Walk-forward evidence | IMPLEMENTED |
| Regime evidence | IMPLEMENTED |
| Chronological paper drawdown/loss-streak aggregation | IMPLEMENTED |
| Caller-supplied paper starting capital | IMPLEMENTED |

The latest evidence-integrity change prevents paper drawdown and consecutive-loss metrics from depending on database return order and prevents a hard-coded ₹1,00,000 starting balance from contaminating evidence for other paper accounts.

## 2.7 Broker architecture

| Capability | Status |
|---|---|
| Canonical broker-independent order model | IMPLEMENTED |
| Dhan abstraction/foundation | IMPLEMENTED |
| Groww abstraction/foundation | IMPLEMENTED |
| Angel One abstraction/foundation | IMPLEMENTED |
| Broker alias normalization | IMPLEMENTED |
| Capability normalization | IMPLEMENTED |
| Broker error normalization | IMPLEMENTED |
| Historical Dhan data integration | IMPLEMENTED |
| Real-money live order integration | INTENTIONALLY LOCKED |

**Broker foundation does not mean production live trading.**

## 2.8 Frontend

| Capability | Status |
|---|---|
| React + TypeScript + Tailwind | IMPLEMENTED |
| Opportunity scanner | IMPLEMENTED |
| Indian/NSE stock search | IMPLEMENTED |
| Keyboard-accessible search | IMPLEMENTED |
| Resilient API error handling | IMPLEMENTED |
| Trade decision UI | IMPLEMENTED |
| Signal evidence presentation | IMPLEMENTED |
| Risk/sizing presentation | IMPLEMENTED |
| Paper trading cockpit | IMPLEMENTED |
| Paper session controls | IMPLEMENTED |
| Strategy readiness cockpit | IMPLEMENTED |
| Performance/evidence views | IMPLEMENTED |
| Runtime error boundary | IMPLEMENTED |
| Resilient navigation | IMPLEMENTED |
| Production TypeScript/Vite build | VERIFIED |

**UI rule:** current product scope is Indian equities. Do not reintroduce US-stock suggestions into Indian-market workflows.

## 2.9 Backend architecture

Major boundaries:

- `backend/app/ai`
- `backend/app/api`
- `backend/app/brokers`
- `backend/app/core`
- `backend/app/db`
- `backend/app/dependencies`
- `backend/app/models`
- `backend/app/providers`
- `backend/app/schemas`
- `backend/app/services`
- `backend/app/tests`

Extend existing service boundaries before creating parallel engines.

## 2.10 Operations/security/deployment

| Capability | Status |
|---|---|
| Docker Compose deployment stack | IMPLEMENTED |
| Backend/frontend containers | IMPLEMENTED |
| PostgreSQL deployment support | IMPLEMENTED |
| DB health check | IMPLEMENTED |
| `/health` liveness | IMPLEMENTED |
| `/ready` database readiness | IMPLEMENTED |
| Required secret configuration | IMPLEMENTED |
| Configurable CORS | IMPLEMENTED |
| Backend CI | IMPLEMENTED |
| Frontend CI/build | IMPLEMENTED |
| Docker configuration validation | IMPLEMENTED |
| Production deployment | ENVIRONMENTAL |
| Continuous scheduler/monitoring runtime | ENVIRONMENTAL |
| External secret-manager integration | FUTURE / DEPLOYMENT |

Never commit broker credentials, JWT secrets, encryption keys or production DB passwords.

---

# 3. Existing detailed documents

Do not duplicate functionality already documented here:

- `docs/V1_COMPLETION_MATRIX.md` — V1 completion matrix
- `docs/V1_RELEASE_CHECKLIST.md` — release/pre-paper checks
- `docs/intraday-strategy.md` — primary intraday strategy
- `docs/algo-research.md` — research notes
- `docs/algo-research-roadmap.md` — research roadmap
- `docs/algo-data-pipeline.md` — algorithmic data pipeline
- `docs/indian-research-pipeline.md` — Indian research pipeline
- `docs/MARKET_DATA_CONTRACT.md` — market-data contract
- `docs/FNO_V1_RESEARCH_PROTOCOL.md` — F&O research protocol
- `docs/REAL_MARKET_TRADING_CHECKLIST.md` — future real-market checklist
- `docs/deployment.md` — deployment guidance

This register is the index/memory layer; detailed documents remain authoritative for their specific technical areas.

---

# 4. Agile product lifecycle

## Phase 0 — Engineering foundation
**Status: COMPLETE / STABILIZED**

Core application, data, signal, risk, paper trading, broker abstractions, deployment and CI exist.

## Phase 1 — Prove the existing intraday strategy
**Status: ACTIVE — CURRENT PRIORITY**

We are not building another strategy. We are proving the existing strategy with reproducible evidence.

Required:
- exact strategy/version/configuration
- exact historical sample/universe
- data-quality validation
- realistic transaction costs
- realistic slippage/impact
- trade count/sample sufficiency
- expectancy/profit factor
- max drawdown
- yearly/monthly stability
- regime stability
- parameter sensitivity
- robustness/stress testing
- walk-forward validation
- untouched out-of-sample validation
- no parameter contamination

## Phase 2 — Paper-market validation
**Status: NEXT**

Compare real-market paper behaviour against historical expectations.

Required:
- reliable market-data runtime
- NSE session handling
- paper-session monitoring
- signal capture
- order/position/exit reconciliation
- net P&L reconciliation
- backtest-vs-paper divergence analysis

## Phase 3 — Strategy readiness
**Status: PARTIALLY IMPLEMENTED / EVIDENCE GATED**

Readiness exists in code, but promotion remains blocked until sufficient evidence is actually observed.

## Phase 4 — Controlled deployment
**Status: ENVIRONMENTAL**

Requires hosting, PostgreSQL, secrets, domain, monitoring, provider credentials, scheduler/runtime and incident handling.

## Phase 5 — Live execution review
**Status: LOCKED**

Live orders remain disabled until independent review of strategy, data, security, operations and broker integration.

---

# 5. Current Agile backlog

| Priority | Feature | Status | Acceptance direction |
|---|---|---|---|
| P0 | Reproduce/document actual multi-year strategy evidence | ACTIVE | Reproducible dataset + config + report |
| P0 | Complete walk-forward/OOS evidence review | NEXT | Explicit train/validation/test evidence |
| P0 | Backtest-vs-paper divergence gate | PLANNED | Detect material degradation before promotion |
| P0 | End-to-end paper session reconciliation | PLANNED | Signals/orders/positions/exits reconcile |
| P1 | Production market-data scheduler | ENVIRONMENTAL | Deployed runtime + provider credentials |
| P1 | Paper monitoring/alerting | PLANNED | Operational visibility |
| P1 | Strategy research dashboard | EXTEND EXISTING | UI over existing evidence engines |
| P1 | Parameter sensitivity visualization | EXTEND EXISTING | UI over robustness outputs |
| P1 | Regime-performance dashboard | EXTEND EXISTING | UI over regime outputs |
| P2 | Additional strategy family | RESEARCH ONLY | Only if existing strategy evidence justifies it |
| P2 | Multi-market support | FUTURE | Must not weaken NSE-first behaviour |
| P3 | Controlled live execution | LOCKED | Separate release gate |

### Current next move

**Do not build a new strategy.** First reproduce and audit the existing multi-year strategy evidence, then complete walk-forward/OOS evidence, then move the qualified strategy into monitored paper trading.

---

# 6. Definition of Done

A feature is complete only when applicable requirements are satisfied:

- Existing implementation checked; no duplicate created.
- Acceptance criteria defined.
- Backend/domain logic implemented.
- API/schema changes implemented where required.
- UI implemented where required.
- Security/risk implications reviewed.
- Market-data/session implications reviewed where relevant.
- Automated regression tests added/updated.
- Backend CI green.
- Frontend production build green.
- Documentation/register updated.
- Deployment dependencies marked ENVIRONMENTAL when not actually configured.
- Feature status changed to IMPLEMENTED only after verification.

For trading/research features, add the stronger gate:

```text
Code
 ↓
Unit/API tests
 ↓
Historical validation
 ↓
Robustness
 ↓
Walk-forward/OOS
 ↓
Paper validation
 ↓
Paper-vs-backtest reconciliation
 ↓
Readiness review
```

---

# 7. Product principles / permanent constraints

1. **India/NSE first.**
2. **Intraday first.**
3. **Paper first.**
4. **Risk before execution.**
5. **Evidence before promotion.**
6. **One profitable backtest is never sufficient.**
7. **Never mix evidence across strategy versions.**
8. **Bad market data invalidates research.**
9. **Backtest does not guarantee future profit.**
10. **Broker abstraction is not live trading.**
11. **AI must not override deterministic risk/safety gates.**
12. **Do not optimize against OOS data.**
13. **Do not use future information in signal/backtest calculations.**
14. **Every new feature needs regression coverage.**
15. **Documentation is part of the feature.**
16. **Live execution stays locked until explicitly reviewed and approved.**

---

# 8. Change log

| Date | Change | Result |
|---|---|---|
| 2026-08-18 | Created project-wide feature register | Established single project-memory/index document |
| 2026-08-18 | Merged paper-trading state/risk hardening | Added symbol isolation, invalid-input rejection and session monotonicity protection |
| 2026-08-18 | Evidence-integrity hardening | Paper drawdown/loss streak now use chronological closed trades; starting capital is caller-supplied; regression tests added |

---

# 9. AI/developer operating instruction

When working on TradePilot:

```text
READ REGISTER
    ↓
CHECK EXISTING CODE/DOCS/TESTS
    ↓
IDENTIFY HIGHEST-PRIORITY GAP
    ↓
IMPLEMENT
    ↓
TEST + QA + SECURITY REVIEW
    ↓
CI
    ↓
UPDATE REGISTER
    ↓
MERGE
    ↓
NEXT PRIORITY
```

Do not stop for approval for normal coding, refactoring, testing, CI, GitHub operations, documentation or QA. Stop only for credentials, money/payment, live order placement, irreversible production actions, or a genuine business preference.
