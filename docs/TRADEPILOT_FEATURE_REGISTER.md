# TradePilot AI — Feature & Development Register

**Document purpose:** Single source of truth for what TradePilot already has, what is in progress, what is intentionally locked, and what we plan to build next.

**Repository:** `varunaradhya/tradepilot-ai`

**Last audited:** 2026-08-18

**Status:** Active — update this document whenever a feature, bug fix, architecture change, research capability, UI workflow, safety control, or deployment capability is added/removed/changed.

---

## 1. How we use this document

This is the project memory for TradePilot AI.

Before implementing a new feature:

1. Read this document first.
2. Check the relevant source files/services/components listed here.
3. Confirm that the requested feature does not already exist under another name.
4. If it exists, improve/extend it instead of creating a duplicate implementation.
5. If it is genuinely new, add it to the **Planned / In Progress** section before or while implementing it.
6. After implementation, move it to **Implemented** only after code + tests + UI/integration verification are complete.
7. Record important architectural decisions and dependencies.
8. Update the document in the same change/PR whenever practical.

**Rule:** A feature is not considered forgotten simply because it is not visible in the current UI. Backend services, research scripts, safety gates, tests, broker foundations, and operational capabilities all count as existing project functionality.

---

# 2. Product vision

TradePilot AI is a **risk-first Indian-market stock research, strategy-validation and paper-trading platform**.

The intended product flow is:

```text
Indian market data
      ↓
Data quality validation
      ↓
Opportunity / scanner
      ↓
Strategy signal
      ↓
Signal evidence + explanation
      ↓
Strategy qualification / readiness
      ↓
Position sizing + risk checks
      ↓
Paper execution safety gate
      ↓
Paper trade lifecycle
      ↓
Performance evidence
      ↓
Historical + paper validation
      ↓
Readiness decision
      ↓
Future controlled live-execution review
```

## Safety boundary

TradePilot is paper-first. Real-money execution is intentionally locked. A successful paper decision must never imply that a real order was or can be placed.

Historical performance is research evidence, not a guarantee of future performance.

---

# 3. Current implementation baseline

The repository currently contains the major V1 foundation across frontend, backend, research, risk, paper trading, broker abstractions, deployment and CI.

### Technology

- React + TypeScript + Tailwind CSS
- FastAPI + Python
- SQLAlchemy
- SQLite for local development/research
- PostgreSQL for deployment
- Docker Compose
- GitHub Actions

### Current engineering state

- V1 stabilization / paper-trading-ready foundation
- Long-first intraday architecture
- Indian/NSE-first market search and presentation
- Deterministic signal path
- Risk-first execution design
- Historical strategy validation infrastructure
- Paper-trading workflow
- Multi-broker abstraction foundations
- Deployment and CI foundations

The repository README reports the latest verification checkpoint as **371 backend tests passing**, with a successful frontend production build and Docker Compose configuration validation. Always rerun the local/CI verification after changes.

---

# 4. Implemented feature inventory

## 4.1 Strategy and quantitative research

| Feature | Status | Notes / source area |
|---|---|---|
| Deterministic long-first intraday signal | IMPLEMENTED | BUY/NEUTRAL explainable signal path |
| Opening Range Breakout strategy | IMPLEMENTED | Existing ORB research candidate |
| 9/20 EMA trend alignment | IMPLEMENTED | Strategy filter |
| Relative-volume confirmation | IMPLEMENTED | Strategy filter |
| ATR-based stop/target | IMPLEMENTED | Strategy/risk logic |
| Extreme opening-gap rejection | IMPLEMENTED | Strategy filter |
| Risk-based position sizing | IMPLEMENTED | Risk engine |
| Maximum capital allocation per trade | IMPLEMENTED | Risk controls |
| No overnight carry for intraday backtest | IMPLEMENTED | Backtest behavior |
| Strategy quality / regime analysis | IMPLEMENTED | Trend/regime/setup-quality analysis |
| Historical backtesting | IMPLEMENTED | Intraday backtest services |
| Walk-forward validation | IMPLEMENTED | Dedicated validation/regression coverage |
| Robustness / stress analysis | IMPLEMENTED | Cost/stress diagnostics |
| Multi-stock historical validation | IMPLEMENTED | Session-safe aggregation |
| Strategy qualification | IMPLEMENTED | Qualification gates |
| Strategy readiness | IMPLEMENTED | Readiness API/cockpit and evidence gates |
| Strategy-version-scoped evidence | IMPLEMENTED | Prevents mixing evidence across versions |
| ORB momentum strategy family | IMPLEMENTED | `ORB_MOMENTUM_V1` research family |
| VWAP mean-reversion strategy family | IMPLEMENTED | `VWAP_MEAN_REVERSION_V2` research family |
| Equity strategy comparison lab | IMPLEMENTED | Cached-data comparison tooling |
| Indian-market research pipeline | IMPLEMENTED | Research/data workflow |
| F&O V1 research protocol | IMPLEMENTED AS RESEARCH PROTOCOL | Not equivalent to live F&O execution |

### Important strategy rule

Do **not** create another "first strategy" unless research proves the existing strategy family is insufficient. The project already contains a strategy research/validation framework.

The current primary intraday research candidate is documented separately in `docs/intraday-strategy.md`.

---

## 4.2 Market data and Indian-market discovery

| Feature | Status | Notes |
|---|---|---|
| Market-provider abstraction | IMPLEMENTED | Provider boundary |
| Historical market-data services | IMPLEMENTED | Historical provider services |
| Intraday candle validation | IMPLEMENTED | Duplicate/missing/stale/out-of-order checks |
| Research data cache | IMPLEMENTED | Local research datasets |
| Instrument master | IMPLEMENTED | NSE equity symbol/security mapping |
| Indian/NSE-first stock search | IMPLEMENTED | Frontend/backend validation |
| Server-side Indian equity validation | IMPLEMENTED | Watchlist/symbol safety |
| Multi-stock opportunity scanner | IMPLEMENTED | Scanner UI + research endpoint |
| Signal-to-trade-decision composition | IMPLEMENTED | Paper decision service |
| Session-aware market-data handling | IMPLEMENTED | NSE session-aware research work |
| Continuous production market-data scheduler | ENVIRONMENTAL | Requires deployed runtime, credentials, market-hours scheduler and monitoring |

---

## 4.3 Signal, decision and explanation layer

| Feature | Status |
|---|---|
| Deterministic signal engine | IMPLEMENTED |
| Long-first BUY architecture | IMPLEMENTED |
| Neutral/no-trade outcome | IMPLEMENTED |
| Signal evidence/explanation | IMPLEMENTED |
| Signal-to-paper-decision workflow | IMPLEMENTED |
| Risk/reward validation | IMPLEMENTED |
| Position sizing calculation | IMPLEMENTED |
| Strategy readiness gate | IMPLEMENTED |
| Central execution safety gate | IMPLEMENTED |
| Duplicate-signal protection | IMPLEMENTED |

---

## 4.4 Risk management and execution safety

| Feature | Status | Notes |
|---|---|---|
| Position sizing | IMPLEMENTED | Risk budget + capital + quantity/order limits |
| Risk/reward validation | IMPLEMENTED | Entry/SL/target/R:R checks |
| Daily risk budget | IMPLEMENTED | Paper risk guard |
| Daily loss limit | IMPLEMENTED | Paper risk guard |
| Trade-count limit | IMPLEMENTED | Session guard |
| Loss-streak protection | IMPLEMENTED | Paper risk/readiness |
| Open-position limit | IMPLEMENTED | Paper risk guard |
| Duplicate-signal protection | IMPLEMENTED | Paper workflow |
| Long-only intraday policy | IMPLEMENTED | Current BUY-first architecture |
| Central execution safety gate | IMPLEMENTED | Broker/order/mode/risk gates |
| LIVE execution lock | IMPLEMENTED / LOCKED | Real-money order execution remains blocked |

---

## 4.5 Paper trading

| Feature | Status |
|---|---|
| Paper trading engine | IMPLEMENTED |
| Long-only paper orchestrator | IMPLEMENTED |
| Paper session lifecycle | IMPLEMENTED |
| Paper market-bar ingestion | IMPLEMENTED |
| Persistent paper trades | IMPLEMENTED |
| Paper trade ledger | IMPLEMENTED |
| Paper cockpit | IMPLEMENTED |
| Paper performance aggregation | IMPLEMENTED |
| Paper evidence metrics | IMPLEMENTED |
| Paper risk-quality readiness gate | IMPLEMENTED |
| Paper readiness gate | IMPLEMENTED |
| Signal → risk → paper order → position → exit workflow | IMPLEMENTED |

---

## 4.6 Performance and evidence

| Feature | Status |
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
| Strategy qualification evidence | IMPLEMENTED |
| Robustness evidence | IMPLEMENTED |
| Walk-forward evidence | IMPLEMENTED |
| Regime analysis evidence | IMPLEMENTED |

---

## 4.7 Broker architecture

| Feature | Status | Notes |
|---|---|---|
| Canonical order model | IMPLEMENTED | Broker-independent representation |
| Dhan abstraction/foundation | IMPLEMENTED | Capability + adapter boundary |
| Groww abstraction/foundation | IMPLEMENTED | Capability + adapter boundary |
| Angel One abstraction/foundation | IMPLEMENTED | Capability + adapter boundary |
| Broker alias normalization | IMPLEMENTED | Canonical names |
| Capability normalization | IMPLEMENTED | Provider capability checks |
| Broker error normalization | IMPLEMENTED | Consistent failure handling |
| Historical Dhan data integration | IMPLEMENTED | Research data service |
| Real-money live order integration | INTENTIONALLY LOCKED | Separate future release gate |

**Important:** Broker foundation != production live trading.

---

## 4.8 Frontend

| Feature | Status |
|---|---|
| React/TypeScript application | IMPLEMENTED |
| Tailwind UI | IMPLEMENTED |
| Opportunity scanner | IMPLEMENTED |
| Indian-market stock search | IMPLEMENTED |
| Keyboard-accessible stock search | IMPLEMENTED |
| Resilient API error handling | IMPLEMENTED |
| Trade decision UI | IMPLEMENTED |
| Signal evidence presentation | IMPLEMENTED |
| Risk/sizing presentation | IMPLEMENTED |
| Paper trading cockpit | IMPLEMENTED |
| Paper session controls | IMPLEMENTED |
| Strategy readiness cockpit | IMPLEMENTED |
| Performance/evidence views | IMPLEMENTED |
| Runtime error boundary | IMPLEMENTED |
| Resilient application navigation | IMPLEMENTED |
| Production TypeScript/Vite build | VERIFIED |

### UI product principle

The UI should present Indian/NSE equities by default for the current product scope. Do not reintroduce US-stock suggestions into Indian-market workflows unless the feature explicitly requires multi-market support.

---

## 4.9 Backend architecture

Current major application boundaries include:

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

The service layer already contains dedicated research, market-data, strategy, paper-trading, risk, readiness and broker-related functionality. Extend existing service boundaries before creating new parallel services.

---

## 4.10 Operations, security and deployment

| Feature | Status |
|---|---|
| Docker Compose deployment stack | IMPLEMENTED |
| Backend container | IMPLEMENTED |
| Frontend container | IMPLEMENTED |
| PostgreSQL deployment support | IMPLEMENTED |
| DB health check | IMPLEMENTED |
| `/health` liveness endpoint | IMPLEMENTED |
| `/ready` database readiness endpoint | IMPLEMENTED |
| Required secret configuration | IMPLEMENTED |
| Configurable CORS | IMPLEMENTED |
| CI backend tests | IMPLEMENTED |
| CI frontend build | IMPLEMENTED |
| Docker configuration validation | IMPLEMENTED |
| Runtime error boundary | IMPLEMENTED |
| Production deployment | ENVIRONMENTAL |
| Continuous scheduler/monitoring runtime | ENVIRONMENTAL |
| External secret-manager integration | FUTURE / DEPLOYMENT |

Never commit broker credentials, JWT secrets, encryption keys or production database passwords.

---

# 5. Existing project documents — do not duplicate functionality

These documents already exist and should be used as detailed references:

- `docs/V1_COMPLETION_MATRIX.md` — V1 engineering completion matrix
- `docs/V1_RELEASE_CHECKLIST.md` — release and pre-paper-production checks
- `docs/intraday-strategy.md` — primary intraday strategy research candidate
- `docs/algo-research.md` — algorithmic research notes
- `docs/algo-research-roadmap.md` — research roadmap
- `docs/algo-data-pipeline.md` — algorithmic data pipeline
- `docs/indian-research-pipeline.md` — Indian-market research pipeline
- `docs/MARKET_DATA_CONTRACT.md` — market-data contract
- `docs/FNO_V1_RESEARCH_PROTOCOL.md` — F&O research protocol
- `docs/REAL_MARKET_TRADING_CHECKLIST.md` — future real-market readiness checklist
- `docs/deployment.md` — deployment guidance

This feature register is the **index and memory layer**. The detailed documents remain authoritative for their specific technical areas.

---

# 6. Current lifecycle / roadmap

## Phase 0 — Engineering foundation

**Status: COMPLETE / STABILIZED**

Core application, database, frontend, market data, signal, risk, paper trading, broker abstractions, deployment and CI are implemented.

## Phase 1 — Strategy evidence

**Status: ACTIVE**

Goal: prove that the existing strategy research is robust rather than simply profitable in one historical run.

Required evidence:

- historical sample definition
- exact strategy/version definition
- transaction costs
- slippage assumptions
- trade count
- expectancy
- profit factor
- drawdown
- yearly/monthly stability
- regime behavior
- parameter sensitivity
- robustness/stress testing
- walk-forward validation
- out-of-sample validation

## Phase 2 — Paper-market validation

**Status: NEXT**

Goal: compare live-market paper execution against historical expectations.

Required:

- reliable market-data runtime
- NSE session handling
- paper session monitoring
- signal capture
- order/position lifecycle reconciliation
- paper performance evidence
- backtest-vs-paper divergence analysis

## Phase 3 — Strategy readiness

**Status: PARTIALLY IMPLEMENTED / EVIDENCE GATED**

The readiness framework exists. Promotion must remain conservative until the required evidence is actually observed.

## Phase 4 — Controlled deployment

**Status: ENVIRONMENTAL**

Requires:

- chosen cloud hosting
- production PostgreSQL
- secrets
- domain/frontend deployment
- monitoring
- provider credentials
- scheduler/runtime
- operational incident handling

## Phase 5 — Future live-execution review

**Status: LOCKED**

Live orders must remain disabled until independent review of strategy evidence, data quality, operational controls, security and broker integration.

---

# 7. Planned features / backlog

This section is intentionally conservative. A feature must not be added here if equivalent functionality already exists elsewhere in the repository.

| Priority | Feature | Status | Acceptance direction |
|---|---|---|---|
| P0 | Reproduce and document the actual multi-year strategy evidence | PLANNED | Reproducible dataset, configuration and report |
| P0 | Complete walk-forward/OOS evidence review | PLANNED | Explicit train/validation/test results |
| P0 | Backtest-vs-paper divergence gate | PLANNED | Detect material degradation before promotion |
| P0 | End-to-end paper session reconciliation | PLANNED | Signals, orders, positions and exits reconcile |
| P1 | Production market-data scheduler | ENVIRONMENTAL | Real deployed runtime + provider credentials |
| P1 | Paper monitoring/alerting | PLANNED | Operational visibility for live paper sessions |
| P1 | Strategy research dashboard | PLANNED / EXTEND EXISTING | Surface existing evidence without duplicating engines |
| P1 | Parameter sensitivity visualization | PLANNED / EXTEND EXISTING | UI over existing robustness outputs |
| P1 | Regime-performance dashboard | PLANNED / EXTEND EXISTING | UI over existing regime evidence |
| P2 | Additional strategy family | RESEARCH ONLY | Only after V1 strategy evidence justifies it |
| P2 | Multi-market support | FUTURE | Do not weaken NSE-first behavior |
| P3 | Controlled live execution | LOCKED | Separate release after all safety gates |

---

# 8. Known product principles and constraints

1. **India/NSE first.** Current stock discovery and opportunity workflows should prioritize Indian equities.
2. **Paper first.** Real-money execution remains disabled.
3. **Risk before execution.** Every trade decision must pass risk and safety gates.
4. **Evidence before promotion.** One profitable backtest is never sufficient.
5. **No duplicate engines.** Extend existing services/components where the capability already exists.
6. **Strategy versions matter.** Never mix evidence from unrelated strategy versions.
7. **Data quality matters.** Bad candles can invalidate research and paper results.
8. **Backtest ≠ future profit.** Results are research evidence only.
9. **Broker abstraction must remain broker-independent.** Provider-specific behavior belongs behind adapter boundaries.
10. **Production capabilities must be real.** Do not mark a scheduler, broker, deployment or monitoring capability as production-ready merely because a mock/foundation exists.
11. **Tests are part of the feature.** New functionality requires appropriate regression coverage.
12. **Documentation is part of the feature.** New functionality must update this register.

---

# 9. Definition of Done for new features

A new feature is complete only when applicable items below are satisfied:

- [ ] Existing implementation checked first; no duplicate feature created.
- [ ] Requirement/acceptance criteria defined.
- [ ] Backend/domain logic implemented where required.
- [ ] API/schema changes implemented where required.
- [ ] Frontend/UI implemented where required.
- [ ] Security/risk implications reviewed.
- [ ] Market-data/session implications reviewed where relevant.
- [ ] Automated tests added/updated.
- [ ] Existing regression suite remains green.
- [ ] Frontend production build remains green.
- [ ] Documentation updated.
- [ ] Feature status moved to IMPLEMENTED only after verification.
- [ ] Any deployment/environment requirement marked ENVIRONMENTAL instead of falsely marked complete.

---

# 10. Change log

| Date | Change | Result |
|---|---|---|
| 2026-08-18 | Created project-wide feature register after repository audit | Establishes single memory/index document |

---

# 11. AI/developer instruction for future TradePilot work

When working on TradePilot AI, treat this file as persistent project context.

**Before coding:**

```text
Read feature register
      ↓
Locate existing implementation
      ↓
Understand current architecture
      ↓
Check tests/docs
      ↓
Decide: extend existing OR create genuinely new feature
```

**After coding:**

```text
Implementation
      ↓
Tests
      ↓
Build/verification
      ↓
Update this register
      ↓
Update detailed technical document if needed
      ↓
Commit code + documentation together
```

If a future request conflicts with an existing safety boundary, readiness gate, or intentional lock, call that out before changing it.

---

## 12. Audit limitation

This register was created from the repository's current README, completion/release documentation, research documentation, repository structure and identified implementation areas. It is intended to be continuously refined as individual source files are reviewed or changed.

When a future development task touches a subsystem, perform a deeper source-level audit of that subsystem and update this document with the concrete files, endpoints, services, components and tests involved.
