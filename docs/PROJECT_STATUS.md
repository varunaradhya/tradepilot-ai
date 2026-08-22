# TradePilot AI — Persistent Project Status

Last updated: 2026-08-22

## How to use this file

This is the handoff/checkpoint for future TradePilot sessions. Before starting new work, read this file and `TRADEPILOT_DEVELOPMENT_AND_QA.md` so completed work is not repeated.

## Current milestone

**Milestone: F&O strategy qualification — frozen walk-forward / out-of-sample gates**

Status: **IN PROGRESS — QUALIFICATION EVIDENCE REQUIRED**

### Verified latest QA cycle

- Full backend pytest suite is green after correcting time-dependent historical-candle tests to use deterministic IST test time.
- Completed-candle filtering, invalid OHLC rejection, duplicate timestamp handling and chronological ordering are covered.
- Dhan authentication/refresh foundation is complete.
- Autonomous F&O direction/CE/PE/strike/lot selection and cost-aware risk/reward gates are implemented.
- Historical replay is anti-look-ahead by construction: decisions use only bars through the current index and the option-chain snapshot at that index.
- Historical backtest uses next-bar contract resolution, ask-side entry and bid-side exit and refuses stale quote substitution.

### Historical backtest milestone implemented

- Added `backend/app/services/fno_backtest_service.py`.
- Added `backend/app/tests/test_fno_backtest_service.py`.
- Produces trade ledger, equity curve, return, win rate, profit factor, expectancy and max drawdown.
- Applies slippage, transaction costs, capital/risk/lot-size gates and conservative stop/target handling.
- Regression fixture was corrected to model a real next-bar entry and later-bar exit under the configured risk gate.

### New qualification milestone

- Added `backend/app/services/fno_qualification_service.py`.
- Added `backend/app/tests/test_fno_qualification_service.py`.
- Qualification is deliberately evaluation-only: it does not optimize strategy parameters.
- Separates in-sample and out-of-sample trade results.
- Requires minimum trade counts, positive expectancy, minimum profit factor and bounded drawdown in both samples.
- Explicitly fails qualification when OOS evidence is absent.

## Critical limitation

We still do **not** have evidence that the strategy is profitable. The qualification service is only a gate over supplied results. We must obtain sufficiently large, timestamp-aligned historical expired-option datasets with realistic bid/ask evolution before calling the strategy qualified. Synthetic fixtures are for software tests only and must never be presented as performance evidence.

## Current priority queue

1. **Obtain/ingest real historical F&O evidence**
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
- deterministic IST clock handling in historical-candle tests.

## Live trading status

**LOCKED.** No live broker execution should be enabled as a shortcut around qualification gates.

## Verification policy

Never mark a milestone green merely because code was committed. A milestone becomes green only after relevant automated tests pass and, where applicable, real/replay evidence is captured.

## Latest implementation commits

- Walk-forward qualification service: `725b8478abcdd6260cda60b696ad8c85ca77e9c8`
- Walk-forward qualification tests: `ec0a8e097b1cc17f6043078ac52b74e4dfbe717a`
- Deterministic historical-candle test fix: `3e9e6d0c7b1acfb6ff4d851e425e8957ad728a34`
- Historical backtest fill-integrity fix: `614a44d110853ab37bcc7c5cc48f663e8f9e19dd`
- Historical backtest regression tests: `3e017402dfe1680fac87327d6b039db600cb8613`
- F&O backtest engine: `9bf31e1f5650bb112c8a624c1e0f6a1639eafbdb`
- F&O backtest tests: `37feee987f1fd025abebcaa10ef16928492a639c`
- QA plan checkpoint: `5bd9fcc7ec316fb990fe5aed41250701404c7a91`
