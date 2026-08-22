# TradePilot AI — Persistent Project Status

Last updated: 2026-08-22

## How to use this file

This is the handoff/checkpoint for future TradePilot sessions. Before starting new work, read this file and `TRADEPILOT_DEVELOPMENT_AND_QA.md` so completed work is not repeated.

## Current milestone

**Milestone: F&O autonomous paper-trading integrity — historical replay foundation**

Status: **IN PROGRESS**

### Completed in the latest QA cycle

- Hardened Dhan intraday candle retrieval with precise Asia/Kolkata session timestamps.
- Filters incomplete candles.
- Rejects invalid OHLC rows.
- Deduplicates candle timestamps.
- Sorts replay candles chronologically.
- Exposes completed-bar/data-quality state from the F&O auto-scan endpoint.
- Added regression coverage for candle normalization.
- Added the project QA control plan.

### Latest replay milestone work completed

- Added `backend/app/services/fno_replay_service.py`.
- Added `backend/app/tests/test_fno_replay_service.py`.
- Replay decisions are generated from `bars[:index + 1]` only.
- Each replay step uses the option-chain snapshot belonging to that exact bar.
- Added a future-bar mutation guard: changing later candles must not change earlier decisions.
- Added input immutability and length-alignment tests.

### Important limitation

The replay service currently proves the **decision-pipeline anti-look-ahead invariant** using supplied historical bars and option-chain snapshots. It is not yet a complete production backtest because expired-options historical data, realistic historical bid/ask evolution, fills, slippage, and portfolio-level accounting still need to be integrated.

## Current priority queue

1. **Finish replay/backtest engine**
   - historical option-chain snapshot ingestion;
   - realistic bid/ask fills;
   - slippage/market-impact scenarios;
   - stop/target event ordering;
   - expiry-day behavior;
   - trade ledger and equity curve;
   - drawdown, expectancy, profit factor and trade-count statistics.
2. **Qualification / anti-overfitting gates**
   - parameter contamination;
   - validation reuse;
   - regime stability;
   - parameter sensitivity;
   - walk-forward and out-of-sample separation.
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
- CI backend/frontend/deployment release gates.

## Live trading status

**LOCKED.** No live broker execution should be enabled as a shortcut around the qualification gates.

## Verification policy

Never mark a milestone green merely because code was committed. A milestone becomes green only after the relevant automated tests pass and, where applicable, real/replay evidence is captured.
