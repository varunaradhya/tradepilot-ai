# TradePilot AI — Development & QA Control Plan

Last updated: 2026-08-22

> **Persistent handoff:** Read `docs/PROJECT_STATUS.md` before starting new work. It records the current milestone, completed foundations and priority queue so work is not repeated across sessions.

## Product rule

TradePilot is an Indian-market trading/research platform. It must fail closed and must not place live broker orders until the required production safeguards are independently validated and the owner explicitly approves live trading.

## Delivery lifecycle

```text
RESEARCH
  ↓
DATA VALIDATION
  ↓
BACKTEST
  ↓
ROBUSTNESS TEST
  ↓
WALK-FORWARD
  ↓
OUT-OF-SAMPLE
  ↓
STRATEGY QUALIFICATION
  ↓
PAPER TRADING
  ↓
PAPER PERFORMANCE GATE
  ↓
READINESS REVIEW
  ↓
LIVE TRADING (LOCKED)
```

## Current primary product: intraday options paper trading

The F&O paper workflow is autonomous. The user supplies paper capital and analysis interval; TradePilot is responsible for:

- direction: bullish / bearish / no trade;
- confidence gate;
- expiry selection;
- CE/PE selection;
- strike selection;
- liquidity/OI/volume/IV/Greeks filtering;
- entry price;
- volatility-aware stop;
- target;
- cost-aware risk/reward;
- exchange lot size;
- risk-budget position sizing;
- virtual order opening;
- live paper position marking;
- virtual stop/target handling;
- net P&L accounting.

No manual strike or lot selection is part of the intended autonomous path.

## Completed foundations

- Indian-market focus and symbol search.
- Market-data validation and session-aware candle handling.
- Execution realism including slippage, market impact and transaction costs.
- Paper P&L corrected to executable/net P&L.
- Gap-through-stop/target handling foundations.
- Risk controls and portfolio/risk infrastructure.
- Walk-forward validation foundations.
- Strategy qualification/readiness foundations.
- Paper-trading state persistence and idempotency foundations.
- Dhan integration foundation.
- Dhan credential encryption/connection flow.
- Dhan authentication error handling and session refresh architecture.
- F&O option-chain integration.
- Autonomous F&O direction → contract → sizing → R:R pipeline.
- Cost-aware F&O position sizing.
- Cost-aware F&O paper P&L.
- Continuous autonomous paper-session waiting behavior.
- CI gates for backend, frontend, deployment configuration and release gate.
- Precise IST Dhan intraday session-window retrieval.
- Completed-bar filtering, OHLC validation, timestamp deduplication and chronological ordering.
- Replay foundation using only the information set available at each completed bar.
- Future-bar mutation guard for anti-look-ahead regression testing.

## Current QA gates

### P0 — Data integrity

- [x] Completed-candle filtering.
- [x] Reject invalid OHLC values.
- [x] Deduplicate candle timestamps.
- [x] Sort candles chronologically.
- [x] Use Asia/Kolkata session boundaries.
- [x] Use precise IST timestamps for Dhan intraday requests.
- [ ] Verify live NIFTY response contains the expected completed-bar count during a real NSE session.
- [ ] Verify stale-data detection under an actual data interruption.
- [ ] Verify out-of-order data rejection against an actual replay/live fixture.

### P0 — Autonomous strategy integrity

- [x] Minimum completed-bar gate.
- [x] Confidence gate.
- [x] No-trade outcome when direction is not sufficiently supported.
- [x] Autonomous CE/PE selection.
- [x] Autonomous strike selection.
- [x] Autonomous lot sizing.
- [x] Cost-aware R:R gate.
- [x] Replay uses only completed bars available at each decision point.
- [x] Future-bar mutation regression guard.
- [ ] Full historical options replay with real historical option-chain snapshots.
- [ ] Parameter contamination test.
- [ ] Validation-reuse test.
- [ ] Regime stability test.
- [ ] Parameter sensitivity test.

### P0 — Paper execution safety

- [x] Paper-only F&O endpoint.
- [x] Live order execution remains separate.
- [x] Duplicate option-position guard.
- [x] Persistent paper positions.
- [x] Automatic virtual position opening only after QUALIFIED.
- [x] Continuous session waits instead of forcing a trade.
- [x] Executable bid used for long-option paper marking/exit decisions.
- [ ] Explicit paper order idempotency key for autonomous session retries.
- [ ] Reconciliation test after backend restart.
- [ ] Duplicate-candle/duplicate-scan test at session level.
- [ ] Broker/data outage recovery test.

### P0 — Risk

- [x] Per-trade risk budget.
- [x] Capital allocation cap.
- [x] Whole-lot sizing.
- [x] Net cost included in stop-risk calculation.
- [x] Minimum net R:R gate.
- [ ] Daily loss enforcement in the autonomous F&O session.
- [ ] Portfolio/sector/concentration enforcement for multi-position F&O.
- [ ] Consecutive-loss protection.
- [ ] Volatility regime risk adjustment.
- [ ] Emergency kill-switch integration test.

### P1 — Options market realism

- [x] Option-chain OI/volume/IV/Greeks/bid/ask inputs.
- [x] Liquidity-aware contract selection foundation.
- [x] Exchange lot-size resolution.
- [x] Bid/ask-aware paper marking.
- [ ] Spread-width gate with configurable maximum.
- [ ] Minimum bid/ask quantity gate.
- [ ] Circuit/price-band handling.
- [ ] Expiry-day behavior validation.
- [ ] Gap-through-option-stop execution test.
- [ ] Slippage stress scenarios for options.

### P1 — Backtesting and qualification

- [x] Walk-forward foundations.
- [x] Qualification/readiness foundations.
- [x] Anti-look-ahead replay foundation.
- [ ] Full intraday options historical replay.
- [ ] Expired-options data integration for unbiased historical option testing.
- [ ] Historical bid/ask/fill simulation.
- [ ] Trade ledger/equity curve/drawdown statistics.
- [ ] Survivorship/universe bias audit.
- [ ] Corporate-action/universe audit where applicable.
- [ ] Out-of-sample qualification report.
- [ ] Minimum trade-count and statistical significance gate.
- [ ] Profit-factor/drawdown/expectancy stability gate.

### P1 — Authentication/session reliability

- [x] Access-token refresh flow.
- [x] Refresh-token rotation.
- [x] Dhan 401 detection.
- [x] Dhan profile validation.
- [ ] Expired access-token end-to-end test during an autonomous paper session.
- [ ] Browser refresh/restart recovery test.
- [ ] Refresh-token revocation test.

## Current known limitations

1. A green CI run proves code/tests pass; it does not prove that the strategy has predictive edge.
2. The replay foundation is currently a deterministic anti-look-ahead harness, not a full historical options backtest.
3. Expired-options historical snapshots with realistic historical bid/ask data are still required for unbiased options replay.
4. Dhan live market data is required for forward paper trading.
5. Dhan access tokens are time-limited; credential refresh must remain user-controlled and secret.
6. Live order placement remains intentionally unavailable to the paper workflow.
7. The autonomous F&O direction model is a strategy candidate, not yet a production-qualified trading edge.
8. Paper trading must be run for an adequate forward sample before any real-money decision.

## Definition of paper-trading success

A session is successful when TradePilot can repeatedly demonstrate that it:

1. uses only completed, valid market data;
2. waits when evidence is insufficient;
3. chooses a complete option trade without manual strike/lot selection;
4. sizes within the configured risk budget;
5. models realistic transaction costs and executable-side prices;
6. prevents duplicate trades;
7. survives authentication refresh, network/data failures and restarts safely;
8. produces a complete auditable decision record; and
9. never sends a broker order in paper mode.

Profit on one day is **not** a qualification criterion by itself.

## Real-money readiness gate

Live trading remains locked until all of the following are independently evidenced:

- robust historical backtest;
- no-look-ahead candle replay;
- walk-forward and out-of-sample validation;
- realistic options execution/cost model;
- statistically meaningful paper-trading sample;
- acceptable drawdown and expectancy;
- failure/recovery testing;
- security and credential audit;
- reconciliation and idempotency audit;
- production monitoring/alerting;
- explicit owner approval.

## Next highest-priority attacks

1. **Finish the historical options replay/backtest engine** — expired option-chain snapshots, bid/ask fills, slippage, stop/target ordering, expiry-day behavior and portfolio statistics.
2. Run parameter-contamination, validation-reuse, regime-stability and parameter-sensitivity tests.
3. Complete paper execution idempotency/reconciliation/outage recovery.
4. Add daily-loss, concentration, consecutive-loss and emergency kill-switch controls.
5. Only after these gates pass, run extended forward paper trading and strategy qualification.
