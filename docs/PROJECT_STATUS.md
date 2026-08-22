# TradePilot AI — Persistent Project Status

Last updated: 2026-08-22

## How to use this file

This is the handoff/checkpoint for future TradePilot sessions. Before starting new work, read this file and `TRADEPILOT_DEVELOPMENT_AND_QA.md` so completed work is not repeated.

## Current milestone

**Milestone: F&O strategy qualification — real historical evidence layer**

Status: **IN PROGRESS — QUALIFICATION EVIDENCE REQUIRED**

### Verified latest QA cycle

- Full backend pytest suite is green after correcting time-dependent historical-candle tests to use deterministic IST test time.
- Completed-candle filtering, invalid OHLC rejection, duplicate timestamp handling and chronological ordering are covered.
- Dhan authentication/refresh foundation is complete.
- Autonomous F&O direction/CE/PE/strike/lot selection and cost-aware risk/reward gates are implemented.
- Historical replay is anti-look-ahead by construction: decisions use only bars through the current index and the option-chain snapshot at that index.
- Historical backtest uses next-bar contract resolution, ask-side entry and bid-side exit and refuses stale quote substitution.
- Qualification service evaluates frozen IS/OOS results and does not tune strategy parameters.

### New historical evidence layer

- Added `backend/app/services/fno_historical_data_service.py`.
- Added `backend/app/tests/test_fno_historical_data_service.py`.
- Historical option snapshots must be timestamped.
- Future quotes relative to the decision timestamp are rejected.
- Execution-grade snapshots require valid bid/ask pairs.
- Empty option chains are rejected.
- Underlying bars and option snapshots must be aligned and chronologically ordered.
- Validation reports invalid rows instead of silently repairing evidence.

## Critical limitation

We still do **not** have evidence that the strategy is profitable. The historical evidence service is a validation boundary; it does not create historical data. We must ingest sufficiently large, timestamp-aligned historical expired-option datasets with realistic bid/ask evolution before calling the strategy qualified. Synthetic fixtures are for software tests only and must never be presented as performance evidence.

## Current priority queue

1. **Ingest real historical F&O evidence**
   - expired NIFTY option contracts;
   - historical option-chain snapshots;
   - timestamp-aligned bid/ask evolution;
   - contract lifecycle and expiry-day behavior.
2. **Run frozen historical replay**
   - freeze strategy parameters before OOS;
   - run in-sample and OOS without tuning OOS;
   - include slippage and transaction costs;
   - capture trade ledger and equity curve.
3. **Qualification / anti-overfitting gates**
   - parameter contamination;
   - validation reuse;
   - regime stability;
   - parameter sensitivity;
   - walk-forward and OOS separation;
   - minimum trade-count/statistical significance.
4. **Paper execution resilience**
   - autonomous request idempotency;
   - restart reconciliation;
   - duplicate scan protection;
   - broker/data outage recovery.
5. **Risk hardening**
   - daily loss limit;
   - concentration limits;
   - consecutive-loss protection;
   - volatility-regime adjustment;
   - emergency kill switch.
6. **Extended forward paper trading** only after the above gates produce evidence.

## Do not repeat

Do not re-implement or re-test as a new feature without first checking this file and `TRADEPILOT_DEVELOPMENT_AND_QA.md`:

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
- replay anti-look-ahead foundation;
- next-bar F&O fill and historical contract-resolution fix;
- corrected next-bar/later-bar backtest regression fixture;
- deterministic IST clock handling in historical-candle tests;
- frozen IS/OOS qualification gate;
- historical snapshot validation boundary.

## Live trading status

**LOCKED.** No live broker execution should be enabled as a shortcut around qualification gates.

## Verification policy

Never mark a milestone green merely because code was committed. A milestone becomes green only after relevant automated tests pass and, where applicable, real/replay evidence is captured.

## Latest implementation commits

- Historical evidence validation service: `493d1ad08e03c56953bb1948b23e8a29dc20bff0`
- Historical evidence validation tests: `6b97e40c18328f85583a14825927096ec8e35209`
- Walk-forward qualification service: `725b8478abcdd6260cda60b696ad8c85ca77e9c8`
- Walk-forward qualification tests: `ec0a8e097b1cc17f6043078ac52b74e4dfbe717a`
- Deterministic historical-candle test fix: `3e9e6d0c7b1acfb6ff4d851e425e8957ad728a34`
- Historical backtest fill-integrity fix: `614a44d110853ab37bcc7c5cc48f663e8f9e19dd`
- Historical backtest regression tests: `3e017402dfe1680fac87327d6b039db600cb8613`
- F&O backtest engine: `9bf31e1f5650bb112c8a624c1e0f6a1639eafbdb`
- F&O backtest tests: `37feee987f1fd025abebcaa10ef16928492a639c`
- QA plan checkpoint: `5bd9fcc7ec316fb990fe5aed41250701404c7a91`
