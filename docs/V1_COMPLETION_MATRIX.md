# TradePilot AI — V1 Completion Matrix

This document is the single source of truth for the V1 completion pass. It prevents feature work from being declared complete while an important workflow is still disconnected.

## 1. Strategy and research

| Requirement | Status | Notes |
|---|---|---|
| Deterministic long-first intraday signal | DONE | BUY/NEUTRAL with explainable evidence |
| Strategy quality/regime analysis | DONE | Trend/regime and setup-quality coverage |
| Historical backtesting | DONE | Backtest services and API coverage |
| Walk-forward validation | DONE | Dedicated validation and regression coverage |
| Robustness/stress analysis | DONE | Cost/stress diagnostics included |
| Multi-stock historical validation | DONE | Session-safe multi-stock research and aggregation |
| Strategy qualification | DONE | Qualification gates are enforced |
| Strategy readiness | DONE | Readiness API/cockpit and paper evidence gates |
| Strategy version-scoped evidence | DONE | Evidence is scoped to the selected strategy version |

## 2. Market data and signal workflow

| Requirement | Status | Notes |
|---|---|---|
| Market provider abstraction | DONE | Provider boundary exists |
| Historical market data | DONE | Historical provider services exist |
| Intraday candle validation | DONE | Duplicate, missing interval, stale/out-of-order checks |
| Multi-stock opportunity scanner | DONE | Scanner UI and research endpoint exist |
| Signal -> trade decision composition | DONE | Paper trade-decision service exists |
| Continuous production market-data scheduler | ENVIRONMENTAL | Requires a deployed runtime, provider credentials, market-hours scheduling and operational monitoring; not represented as a fake local unit-test feature |

## 3. Risk and execution safety

| Requirement | Status | Notes |
|---|---|---|
| Position sizing | DONE | Risk-budget, capital, quantity and order-value limits |
| Risk/reward validation | DONE | Entry/SL/target and R:R checks |
| Daily risk budget | DONE | Paper risk guard |
| Daily loss limit | DONE | Paper risk guard |
| Trade-count limit | DONE | Session guard |
| Loss-streak protection | DONE | Paper risk guard/readiness |
| Open-position limit | DONE | Paper risk guard |
| Duplicate-signal protection | DONE | Paper workflow |
| Long-only intraday policy | DONE | BUY-first architecture |
| Central execution safety gate | DONE | Broker/order/mode/risk gates |
| LIVE execution lock | DONE | LIVE remains explicitly blocked |

## 4. Paper trading

| Requirement | Status | Notes |
|---|---|---|
| Paper trading engine | DONE | Simulation-only engine |
| Long-only paper orchestrator | DONE | Signal -> position lifecycle |
| Paper session lifecycle | DONE | Start/session/close behavior covered |
| Paper market-bar ingestion | DONE | Simulation endpoints exist |
| Persistent paper trades | DONE | Paper trade persistence and ledger hardening |
| Paper cockpit | DONE | UI navigation and operational view |
| Paper performance aggregation | DONE | Persisted evidence aggregation |
| Paper evidence metrics | DONE | Expanded readiness metrics |
| Paper risk-quality readiness gate | DONE | Risk-quality gate feeds readiness |
| Paper readiness gate | DONE | Conservative promotion criteria |

## 5. Performance evidence

| Requirement | Status | Notes |
|---|---|---|
| Win rate | DONE | Evidence analytics |
| Profit factor | DONE | Evidence analytics |
| Expectancy | DONE | Evidence analytics |
| Drawdown | DONE | Evidence/readiness analytics |
| Trade count | DONE | Qualification/readiness |
| Multi-stock aggregation | DONE | Cross-symbol evidence aggregation |
| Strategy-version evidence | DONE | Prevents mixing unrelated strategy versions |
| Historical + paper evidence workflow | DONE | Both evidence classes feed readiness |

## 6. Broker architecture

| Requirement | Status | Notes |
|---|---|---|
| Canonical order model | DONE | Broker-independent order representation |
| Dhan foundation | DONE | Capability and adapter boundary |
| Groww foundation | DONE | Capability and adapter boundary |
| Angel One foundation | DONE | Capability and adapter boundary |
| Broker alias normalization | DONE | Canonical broker names |
| Capability normalization | DONE | Provider capability checks |
| Broker error normalization | DONE | Consistent failure handling |
| Real-money live order integration | INTENTIONALLY LOCKED | Must remain disabled until independent strategy/data/operational review and broker credential validation |

## 7. Frontend

| Requirement | Status | Notes |
|---|---|---|
| Opportunity scanner | DONE | Intraday scanner navigation/UI |
| Trade decision UI | DONE | Signal, risk, sizing and paper status |
| Paper trading cockpit | DONE | Paper session controls and evidence |
| Strategy readiness cockpit | DONE | Readiness visibility |
| Performance/evidence views | DONE | Paper evidence is surfaced |
| Production TypeScript/Vite build | VERIFIED | Latest user checkpoint passed |

## 8. Operations and deployment

| Requirement | Status | Notes |
|---|---|---|
| PostgreSQL deployment stack | DONE | Docker Compose |
| Backend/frontend containers | DONE | Docker Compose |
| DB health check | DONE | Compose dependency health |
| /health liveness endpoint | DONE | Operational monitoring |
| /ready database readiness endpoint | DONE | Dependency readiness |
| Required secret configuration | DONE | JWT and broker encryption key required in deployment |
| Configurable CORS | DONE | Environment-driven |
| CI backend tests | DONE | GitHub Actions |
| CI frontend build | DONE | GitHub Actions |
| Docker configuration validation | DONE | CI hardening |
| Production deployment | ENVIRONMENTAL | Requires user-selected hosting, domain, secrets and broker/provider credentials |

## 9. Final verification gate

Before calling V1 production-ready, verify all of the following locally/in CI:

1. Backend test suite: **0 failures**.
2. Frontend production build: **successful**.
3. Docker Compose configuration: **valid** with real deployment secrets supplied through environment.
4. Paper workflow: scanner -> signal -> risk -> paper order -> position -> exit -> evidence.
5. Readiness workflow: historical qualification + robustness/walk-forward + paper evidence -> readiness decision.
6. Broker workflow: capability detection and canonical errors work for Dhan/Groww/Angel One foundations.
7. LIVE order execution remains blocked.

## 10. Explicit non-goals for V1

- Do not enable unattended real-money trading.
- Do not treat backtest performance as proof of future profitability.
- Do not claim a broker is production-live merely because an adapter foundation exists.
- Do not claim continuous market monitoring is deployed until a real scheduler/runtime and provider credentials are configured and observed in paper mode.

## Definition of Done

TradePilot V1 is engineering-complete when all items marked DONE remain green and the ENVIRONMENTAL items have been explicitly configured and verified in the target deployment environment. Live execution is a separate future release gate, not a V1 default.
