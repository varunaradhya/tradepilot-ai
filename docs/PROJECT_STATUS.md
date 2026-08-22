# TradePilot AI — Persistent Project Status

Last updated: 2026-08-22

## How to use this file

This is the handoff/checkpoint for future TradePilot sessions. Before starting new work, read this file and `TRADEPILOT_DEVELOPMENT_AND_QA.md` so completed work is not repeated.

## Current milestone

**Milestone: F&O autonomous paper-trading integrity — historical replay/backtest engine**

Status: **IN PROGRESS**

### Completed in the latest QA cycle

- Hardened Dhan intraday candle retrieval with precise Asia/Kolkata session timestamps.
- Filters incomplete candles.
- Rejects invalid OHLC rows.
- Deduplicates candle timestamps.
- Sorts replay candles chronologically.
- Exposes completed-bar/data-quality state from the F&O auto-scan endpoint.
- Added regression coverage for candle normalization.
- Added the persistent QA control plan.

### Replay milestone completed

- Added `backend/app/services/fno_replay_service.py`.
- Added `backend/app/tests/test_fno_replay_service.py`.
- Replay decisions are generated from `bars[:index + 1]` only.
- Each replay step uses the option-chain snapshot belonging to that exact bar.
- Added a future-bar mutation guard: changing later candles must not change earlier decisions.
- Added input immutability and length-alignment tests.

### Historical backtest milestone now implemented

- Added `backend/app/services/fno_backtest_service.py`.
- Added `backend/app/tests/test_fno_backtest_service.py`.
- Uses the autonomous replay engine rather than a separate strategy implementation.
- Enforces next-bar entry after a qualified signal.
- Uses ask-side entry and bid-side exit when available.
- Applies configurable slippage and the existing F&O cost model.
- Enforces lot-size, capital-allocation and risk-budget gates.
- Simulates stop/target exits conservatively.
- Produces trade ledger, equity curve, return, win rate, profit factor, expectancy and max drawdown metrics.

### Important limitation

The backtest engine is now structurally complete enough for deterministic replay tests, but it is **not yet evidence of a profitable strategy**. Real expired-options historical snapshots, realistic historical bid/ask evolution, contract lifecycle/expiry handling, and sufficiently large out-of-sample datasets are still required before strategy qualification.

## Current priority queue

1. **Complete historical F&O evidence layer**
   - historical option-chain snapshot ingestion;
   - real expired contracts;
   - realistic historical bid/ask and fill evolution;
   - expiry-day behavior;
   - slippage/market-impact scenarios.
2. **Qualification / anti-overfitting gates**
   - parameter contamination;
   - validation reuse;
   - regime stability;
   - parameter sensitivity;
   - walk-forward and out-of-sample separation;
   - minimum trade-count/statistical significance.
3. **Paper execution resilience**
   - explicit autonomous request idempotency;
   - restart reconciliation;
   - duplicate scan protection;
   - broker/data outage recovery.
4. **Risk hardening**
   - daily loss limit;
   - concentration limits;
   - consecutive-loss protection;
   - volatility-regime adjustment;
   - emergency kill switch.
5. **Extended forward paper trading** only after the above gates produce evidence.

## Do not repeat

Do not re-implement or re-test as a new feature without first checking the QA plan and this status file:

- completed-candle filtering;
- IST Dhan session-window handling;
- invalid OHLC rejection;
- duplicate timestamp removal;
- chronological candle ordering;
- minimum-bar and confidence gates;
- autonomous CE/PE/strike/lot selection;
- cost-aware risk/reward sizing;
- executable-side option paper marking;
- paper-only F&O opening;
- duplicate open-option guard;
- persistent paper-trade lifecycle basics;
- Dhan authentication/refresh foundation;
- CI backend/frontend/deployment release gates;
- replay anti-look-ahead foundation.

## Live trading status

**LOCKED.** No live broker execution should be enabled as a shortcut around the qualification gates.

## Verification policy

Never mark a milestone green merely because code was committed. A milestone becomes green only after the relevant automated tests pass and, where applicable, real/replay evidence is captured.

## Latest implementation commits

- F&O backtest engine: `9bf31e1f5650bb112c8a624c1e0f6a1639eafbdb`
- F&O backtest tests: `37feee987f1fd025abebcaa10ef16928492a639c`
- QA plan checkpoint: `5bd9fcc7ec316fb990fe5aed41250701404c7a91`
