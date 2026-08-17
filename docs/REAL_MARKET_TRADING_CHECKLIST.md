# TradePilot AI — Real-Market Trading Readiness Checklist

This checklist is the product standard for moving from research to paper trading and eventually broker execution. A green UI is not evidence of a profitable system.

## 1. Signal quality
- [x] Trend filter: price > fast EMA > slow EMA.
- [x] Breakout uses prior completed candles only.
- [x] RSI confirmation uses prior-bar momentum.
- [x] Volume confirmation against rolling average.
- [x] ATR volatility regime filter.
- [x] Reject trades with excessive stop distance.
- [x] Minimum risk/reward gate (default 1.8R).
- [ ] Add benchmark/index regime filter (NIFTY 50 / sector index) before live deployment.
- [ ] Add liquidity/average traded-value filter before live deployment.
- [ ] Add spread/quote-quality filter for intraday execution.
- [ ] Add corporate-action/news-event exclusion window where reliable data is available.

## 2. Risk and position sizing
- [x] Risk-based position sizing.
- [x] Maximum capital allocation per position.
- [x] Long-only default.
- [x] Maximum daily loss gate in backtest.
- [x] Maximum trades per day in backtest.
- [x] Paper risk guard supports daily loss, trade count, loss streak and open-position limits.
- [x] Portfolio total-exposure and total-risk gate.
- [x] Sector exposure gate as a conservative correlation proxy.
- [ ] Add max gap-at-entry rule (skip if opening gap invalidates planned risk).
- [ ] Add broker margin/exposure reconciliation before live orders.
- [ ] Add historical correlation matrix for portfolio-level correlation limits.

## 3. Stop loss and trade management
- [x] Initial stop is ATR-based.
- [x] Stop cannot be widened after entry.
- [x] Gap-through-stop fills at executable market/open price in backtest.
- [x] Trailing stop activates after a configurable R multiple.
- [x] Trailing stop uses current ATR and only ratchets upward for long trades.
- [x] Target remains protected by trailing logic.
- [x] Maximum holding period is enforced.
- [ ] Add breakeven transition policy as an explicit strategy option.
- [ ] Add partial-profit policy only after it is validated by out-of-sample testing.
- [ ] Add end-of-day forced exit policy for strategies that are not intended to hold overnight.

## 4. Execution realism
- [x] Next-bar execution prevents look-ahead bias.
- [x] Buy and sell slippage are modeled separately.
- [x] Brokerage/transaction costs are included.
- [x] Database-backed paper-trade P&L uses the same Indian equity round-trip cost model as research.
- [x] Gap handling is conservative.
- [ ] Model spread and queue/partial fills for intraday strategies.
- [ ] Track signal timestamp, order-submit timestamp, acknowledgement timestamp and fill timestamp.
- [ ] Track p50/p95/p99 order latency.
- [x] Reject stale signals after a configurable TTL in execution guard.
- [x] Enforce Indian cash-market session and injectable exchange-holiday checks when market context is supplied.
- [x] Enforce supplied lower/upper price bands before paper execution.

## 5. Backtesting standard
- [x] No same-candle signal execution.
- [x] Final-bar signal cannot create a phantom trade.
- [x] Stop-first assumption when OHLC cannot establish intrabar order.
- [x] Max drawdown and profit factor reported.
- [x] Expectancy per trade reported.
- [ ] Add out-of-sample split and walk-forward testing.
- [ ] Add parameter sensitivity / robustness testing.
- [ ] Add survivorship-bias-safe universe snapshots.
- [ ] Add delisted/illiquid symbol handling where historical data permits.
- [ ] Require minimum trade count and stability thresholds before strategy promotion.

## 6. Monitoring and operational safety
- [x] Market-data freshness guard.
- [ ] Market-data heartbeat and stale-feed alarm UI/alerting.
- [ ] Broker API heartbeat.
- [x] Order acknowledgement timeout guard.
- [ ] Position reconciliation against broker every cycle.
- [x] Duplicate-order/idempotency protection at the paper execution boundary.
- [x] Kill switch that blocks all new paper entries immediately.
- [ ] Emergency flatten procedure.
- [ ] Daily API-session logout / token lifecycle handling.
- [ ] Immutable audit log for signals, risk decisions, orders and fills.
- [ ] Alert on rejected orders, abnormal latency, price gaps, missing candles and P&L anomalies.

## 7. Profitability gates
A strategy must NOT be promoted because its backtest return is high.

Minimum promotion evidence should include:

1. Positive expectancy after costs and slippage.
2. Acceptable maximum drawdown.
3. Profit factor comfortably above 1 after costs.
4. Stable results across multiple market regimes.
5. Out-of-sample performance close enough to in-sample performance.
6. No single trade/day/month responsible for most of the return.
7. Sensitivity to parameters is reasonable; no single magic value.
8. Paper trading behaves close to the backtest execution model.
9. Operational failure tests pass.
10. Only then consider broker integration.

## 8. Execution-speed targets
These are engineering targets, not promises of profitability:

- Market-data processing: <100 ms p95 for a normal event.
- Signal evaluation: <250 ms p95 for one symbol on cached data.
- Risk decision: <25 ms p95 locally.
- Order construction: <25 ms p95 locally.
- Broker round-trip latency: measure, do not assume; alert on p95/p99 degradation.
- Stale signal TTL: strategy-specific; never submit an order from an expired signal.

## 9. Regulatory / broker readiness
NSE/SEBI retail-algo rules are a release gate, not a documentation afterthought. Current SEBI retail-algo policy is designed around safer retail participation, with the current framework applicable to brokers from April 1, 2026. Order-level controls include price and quantity checks and broader risk-control requirements. Re-check broker/exchange implementation standards immediately before enabling automated live orders.

Sources reviewed:
- SEBI circular on safer participation of retail investors in algorithmic trading.
- SEBI extension/implementation timeline for the retail-algo framework.
- SEBI master circular provisions on algorithmic order risk controls and dysfunctional-algo monitoring.
- NSE market timings.
- Zerodha educational/disclosure material on trading-system execution and stop-loss behavior.

The product must remain paper-first until every live-execution release gate is independently verified.
