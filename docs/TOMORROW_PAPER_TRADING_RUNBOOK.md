# TradePilot AI — Real-Market Paper Trading Runbook

## Purpose

Use TradePilot during a real NSE market session while keeping **all execution simulated**. No broker order placement is permitted.

## Start here

For tomorrow's first run, use the **web frontend**, not the CLI. The frontend is the customer-facing control surface; the backend API performs the paper-trading engine work. The repository provides `npm run dev` for the frontend and Docker Compose for the complete application.

### Preferred local start

From the repository root:

```powershell
$env:POSTGRES_PASSWORD = "<strong-local-password>"
$env:TRADEPILOT_JWT_SECRET = "<strong-local-jwt-secret>"
$env:TRADEPILOT_BROKER_ENCRYPTION_KEY = "<strong-local-encryption-key>"
docker compose up --build
```

Then open:

```text
http://localhost:8080
```

Backend health:

```text
http://localhost:8000/health
http://localhost:8000/ready
```

If Docker is not being used, start the backend and frontend separately. Frontend development is `npm.cmd run dev` from `frontend`; backend development uses the existing FastAPI application. Do not invent a new paper-trading CLI.

## Pre-market checklist

Do this before 09:15 IST:

- [ ] Confirm repository is on the latest `main`.
- [ ] Confirm CI is green for the commit being used.
- [ ] Confirm backend `/health` = healthy.
- [ ] Confirm backend `/ready` = database available.
- [ ] Confirm paper mode says `SIMULATION_ONLY`.
- [ ] Confirm live execution is disabled.
- [ ] Confirm kill switch status is known.
- [ ] Confirm market-data provider is available.
- [ ] Confirm the intended Indian/NSE symbols and interval.
- [ ] Confirm strategy authorization/readiness for the selected symbol(s).
- [ ] Do not connect or enable real-money broker order placement.

## Market-session test

### 09:15–09:20

Observe only.

Check:

- market session recognized as active
- candles arrive in chronological order
- timestamps are Asia/Kolkata-correct
- no stale/future candles
- no duplicate candles
- no US/non-Indian symbol suggestions

Do not judge the strategy from the first few minutes.

### During the session

Use the frontend to observe:

- signals
- paper positions
- entry/exit prices
- stop-loss
- target
- trailing stop
- quantity/risk
- gross P&L
- costs
- **net P&L**
- daily loss
- exposure
- reconciliation status
- data freshness

The backend paper API already exposes paper dashboard/session/performance functionality; direct arbitrary paper-trade creation is intentionally disabled.

## Mandatory evidence to capture

For every generated signal/trade:

```text
signal/request ID
symbol
strategy version
interval
signal timestamp
entry
simulated fill
quantity
stop
 target
exit
exit reason
slippage
transaction costs
gross P&L
net P&L
market regime
reconciliation status
```

## Adversarial tests during paper trading

Do not manually create fake orders in the live market. Instead observe whether the system handles these naturally:

1. stale market data
2. missing candle
3. duplicate signal/request
4. invalid price
5. market/session boundary
6. stop-loss gap
7. target gap
8. rapid price movement
9. broker/data-provider interruption
10. restart with an open paper position
11. reconciliation mismatch
12. daily-loss limit

Expected behavior is always safe degradation, not forced execution.

## End-of-day checklist

After 15:30 IST:

- [ ] No open paper position remains unintentionally.
- [ ] Session-close handling is correct.
- [ ] Every paper trade is reconciled.
- [ ] Net P&L is consistent with ledger.
- [ ] No duplicate trades.
- [ ] No missing trades/signals.
- [ ] No stale-data execution occurred.
- [ ] Record total trades.
- [ ] Record win rate.
- [ ] Record profit factor.
- [ ] Record expectancy.
- [ ] Record max drawdown.
- [ ] Record consecutive losses.
- [ ] Record backtest-vs-paper divergence.

## Interpretation rule

One trading day is **not** strategy validation.

Do not promote or change parameters because of one profitable or losing session.

Paper evidence should accumulate across many sessions and should be compared with the locked historical/OOS evidence.

## Safety boundary

The system must remain:

```text
SIMULATION_ONLY
live_execution_allowed = false
```

If anything suggests that a real broker order could be submitted, **stop the session immediately** and investigate before continuing.

## First objective

Tomorrow's objective is not to make money.

The objective is to answer:

> Can TradePilot reliably consume real Indian-market data, generate its existing strategy signals, simulate execution realistically, record net P&L, and fail safely when data/execution conditions are abnormal?

Only after repeated paper evidence answers that question positively should a separate live-trading safety review be considered.
