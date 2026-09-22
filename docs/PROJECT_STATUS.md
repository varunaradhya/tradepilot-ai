# TradePilot AI — Persistent Project Status

Last updated: 2026-09-22

## How to use this file

This is the handoff/checkpoint for future TradePilot sessions. Before starting new work, read this file, `TRADEPILOT_DEVELOPMENT_AND_QA.md`, and `ENHANCEMENT_LEDGER.md` so completed work is not repeated. The enhancement ledger is the canonical change/fix history.

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

### New historical evidence ingestion layer

- Added `backend/app/services/fno_historical_ingestion_service.py` and tests.
- Added deterministic normalization for Dhan expired rolling-option responses into timestamped option bars/snapshots.
- The adapter preserves OHLC/OI/IV/volume/spot and explicitly marks these observations as non-execution-grade because Dhan's expired-options API does not provide historical best bid/ask.
- The adapter never copies close/LTP into bid/ask and rejects duplicate timestamp/strike/side observations.
- Dhan's expired-options endpoint can therefore supply real historical contract/market evidence for the research layer, but it is **not sufficient by itself for execution-grade qualification**; a historical executable bid/ask source is still required.

### F&O QA hardening — executable quote boundary

- Canonical enhancement/fix ledger created at `docs/ENHANCEMENT_LEDGER.md`; recent quote, replay, historical-fill, paper-safety and authentication changes are consolidated there with commits and evidence status.

- Added replay chronology validation: supplied bar timestamps, when present, must be numeric and strictly increasing. This prevents duplicated/out-of-order bars from silently becoming time-aligned research evidence.
- Added dummy-data tests for chronological rejection and executable quote behavior. The standalone sanity harness passed: LTP-only SELL quote rejected (`0`), valid BUY used ask (`120`), valid SELL used bid (`119`).
- Repository test execution remains pending because GitHub currently exposes no workflow runs/status for these commits and the execution environment cannot clone the repository from the network; no CI-green claim is being made.

- Added deterministic dummy-data regression coverage for next-bar entry, missing-bid handling, and end-of-test liquidation using executable bid only.
- Local focused harness also verified BUY uses ask, SELL rejects missing bid, and SELL uses valid bid; this is supplementary to the repository tests.
- Continuing QA into replay future-invariance, expiry/session boundaries, duplicate paper positions, and failure/retry behavior before historical qualification.

- Follow-up audit found and corrected a quote-guard regression introduced during hardening: bid/ask values are now initialized before validation.
- Paper position marking no longer falls back from missing executable bid to LTP; missing bid leaves the position unmarked rather than fabricating an executable exit.
- Added regression coverage for quote responses containing LTP without bid/ask.

- Audited the autonomous F&O selection, decision, and historical replay paths for executable-price fallbacks.
- Fixed autonomous F&O decisioning so a missing/invalid ask produces `NO_TRADE` instead of substituting LTP.
- Fixed option-contract selection so missing/invalid bid/ask is rejected before a contract can qualify.
- Fixed historical F&O backtesting so entry uses ask-side quotes and exit uses bid-side quotes only; LTP/close is never a simulated executable fill.
- Added regression tests covering missing ask/bid and LTP-only historical snapshots.

### New historical evidence layer

- Added `backend/app/services/fno_historical_data_service.py`.
- Added `backend/app/tests/test_fno_historical_data_service.py`.
- Historical option snapshots must be timestamped.
- Future quotes relative to the decision timestamp are rejected.
- Execution-grade snapshots require valid bid/ask pairs.
- Empty option chains are rejected.
- Underlying bars and option snapshots must be aligned and chronologically ordered.
- Validation reports invalid rows instead of silently repairing evidence.


### Current QA batch — restart safety, quote integrity, and CI repair

- Current GitHub HEAD is `2045c27659cf304f517fad6e1b2fe5a63a2b2e17`; this batch was based on that live branch state.
- Repaired a CI-blocking literal escape in `paper_signal_request_service.py` that caused backend `compileall` SyntaxError.
- F&O completed-request replay now verifies the persisted fingerprint before replay; request-id reuse for a different signal is rejected.
- Completed request replay is now evaluated before session/risk gates, while new requests remain subject to the session gate.
- F&O paper entry now consults the existing durable kill switch and fails closed when active; no new unlock path was introduced.
- Historical evidence validation now rejects option snapshots whose timestamps do not exactly align with the underlying bar timestamp.
- Paper-ledger reconciliation now validates restored open-position identity by symbol/security ID instead of incorrectly treating every engine open position as divergent.
- Added regression coverage for stale/fresh PENDING recovery, ledger identity, kill-switch gate behavior, future-trade isolation, inverted quotes, timestamp misalignment, and invalid stress slippage.
- Execution-friction stress validation now rejects negative slippage before any scenario backtest runs.
- The qualification status remains blocked pending real timestamp-aligned historical bid/ask evidence; no synthetic result was promoted to performance evidence.

### Restart reconciliation and broker resilience batch — 2026-09-22

- Crash-left PENDING F&O paper requests are now reconciled only when the exact request fingerprint matches and exactly one matching persisted open option trade can be proven from contract identity, quantity, prices, strategy version, and request/trade chronology.
- Reconciliation never creates a trade and never automatically retries an order. Ambiguous or unmatched PENDING requests remain recovery-required.
- Added `GET /fno/paper/recovery` to expose durable pending/recovery state without retrying anything.
- Dhan retry backoff now bounds provider-supplied `Retry-After` values to 20 seconds and falls back safely for invalid/negative values; regression coverage added for 429/503 retry behavior and exhaustion.
- Historical Dhan rolling-option normalization now rejects duplicate timestamps within a contract response instead of silently retaining ambiguous observations.
- Live execution remains hard-locked and no broker credentials/tokens were requested or used.
- CI is still being verified against the latest push; previous workflow runs were cancelled/replaced while this batch was being committed, so no green claim is made until the final run completes.

### Latest batched F&O QA hardening

- Paper risk timestamps now normalize both timezone-aware and SQLite-naive closed-trade timestamps safely.
- Exact completed F&O paper requests are checked for replay before mutable session/risk gates, so a duplicate request cannot be rejected merely because risk state changed after the original acceptance.
- Crash-left PENDING paper requests can now be identified as stale without automatically retrying them. Automatic retry remains intentionally disabled until restart reconciliation is proven at the process/database boundary.
- Historical F&O replay now supports an optional maximum bid/ask spread gate.
- Added a frozen execution-friction stress runner that varies only slippage and spread assumptions; it does not tune strategy parameters.
- Added an optional minimum top-of-book bid/ask quantity filter when provider depth includes quantity.
- Added regression coverage for spread rejection/acceptance, stress scenario enumeration, stale pending detection, timezone normalization, and top-of-book quantity filtering.
- These changes do not create historical bid/ask evidence. Real execution-grade historical options data remains the qualification blocker.

## Critical limitation

We still do **not** have evidence that the strategy is profitable. The historical evidence service is a validation boundary; it does not create historical data. We must ingest sufficiently large, timestamp-aligned historical expired-option datasets with realistic bid/ask evolution before calling the strategy qualified. Synthetic fixtures are for software tests only and must never be presented as performance evidence.

## Current priority queue

1. **Ingest real historical F&O evidence**
   - expired NIFTY option contracts;
   - historical option-chain snapshots;
   - timestamp-aligned bid/ask evolution;
   - contract lifecycle and expiry-day behavior;
   - execution-grade historical bid/ask source (Dhan expired OHLC alone is not enough).
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
- historical snapshot validation boundary;
- Dhan expired-option response normalization without fake bid/ask.

## Live trading status

**LOCKED.** No live broker execution should be enabled as a shortcut around qualification gates.

## Verification policy

Never mark a milestone green merely because code was committed. A milestone becomes green only after relevant automated tests pass and, where applicable, real/replay evidence is captured.

## Latest implementation commits

- F&O idempotency/candle identity: `ab6ae24ebc9acae11c9074e3a78256b4fbcb05a6`, `b47be9fe18377433a4de23b9ba0941bcff39eb99`
- F&O quote outage hardening: `cd8c65774c8c6dd442403bf4aadbf61217573c22`
- Conservative gap-through replay: `f26e399a05aa8077c422a89f5477764d084f749f`, test `ef04997c30adddbfb35aea08f46a7810597f4529`
- F&O risk integration: `0f8ce98498af580f44c047f70145ef1072f76591`, test `5836a8bb1639e03de6f74bf1a7789c97f9b0eabd`
- Batched F&O safety/realism hardening: `824d0c0`, `c3557205`, `787b6bb1`, `576afe8f`, `d420c448`, `ed8ad1ae`, `19a649ad`, `a56b0513`, `74c4f841`, `bd9b84ed`, `9c2b0d96`, ledger `3942af27`
- Current QA repair/hardening batch: `77908ced`, `bbb2d5b5`, `63f88177`, `f86aed01`, `4e7fc427`, `c8e257f3`, `69207bd0`, `37df0f0e`, `ed6decca`, `7ac3e8cb`, `ad91ff17`, `2a8db1e0`, `2045c276`
- Restart/recovery + broker resilience batch: `c6e41ff2`, `a8750c63`, `b6a2dcf9`, `7ab7b78a`, `5d7bd6cd`, `6173a699`, `568e2b72`, `d1ab819f`
- Follow-up execution identity hardening: `f5a602de`, `019676a0`
- Live execution hard lock: `2155244ff7ed0fff7a01824f7f91a53c0d841c16`, test `10f9d19f4993f2a20950972bb9c26bafad98ca3c`

- F&O session/freshness hardening: `914115460df874c286ed538a3358d717c1cc85a6`
- Deterministic F&O freshness gate: `c5837d55ccc8966740a75cc01106a6349c35746f`
- F&O session/freshness tests: `4516c566ddb2da9d10f5fc4d77f1f85569bc3d3a`

- F&O expiry validation: `f349b2795973c268dc59736e3355366e1c70e4ac`
- F&O expiry regression tests: `d8e210232f27654b3dd48feca76527dd9b3df7d4`
- Operations/reconciliation foundation audit recorded in enhancement ledger.

- F&O paper idempotency integration: `4f9e5f45f2cd4ae31f9cd70c54e8228a6440196f`, lifecycle fix `03ba9bd9c6101e8073518e12e12f385f054ea754`, collision guard `e8fd79c910714b42cd9479b93fe430e88ca801af`

- Enhancement ledger reconciliation: `3cb09e191e3e8f94866b437bbc0126a6a65d09b1`
- QA handoff now references canonical ledger: `9ab8a9aafb3f52e62a8e81f7714ccdcfc5ea5ab9`

- Canonical enhancement/QA ledger: `f642e89ad443cd50397b88856b99e8486f0b6129`

- F&O executable quote hardening: `13581e0bc188043dd47d4560bb14a1806f10389a` (backtest), `dcfe81507c8158ad11c2836f2b01a59e58904eee` (selection), `8358c47371740929fedaed62fe7a613f1cfee9ea` (autonomous decision)
- F&O executable quote regression tests: `6230330aa8db1bd48454f1c39c4c33bc11a5e14a`

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
