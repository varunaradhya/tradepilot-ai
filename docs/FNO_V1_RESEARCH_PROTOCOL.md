# F&O Strategy V1 — Research Protocol

## Objective

TradePilot V1 is deliberately **one fixed, deterministic intraday strategy**. We do not optimize parameters against the final test period and we do not promote a strategy because one backtest is profitable.

### Strategy

**NIFTY 5-minute Opening Range Breakout + EMA trend + VWAP + RSI + volume confirmation**.

- Build 5-minute bars.
- Opening range = first three bars (09:15–09:30 IST).
- Long only when price breaks the opening-range high, price > EMA20 > EMA50, price > session VWAP, RSI is 55–70, and current volume is at least 1.2x the previous 20-bar average.
- Short is the mirror condition: opening-range low break, price < EMA20 < EMA50, price < VWAP, RSI 30–45, volume >= 1.2x average.
- ATR(14) sets the stop at 1 ATR and target at 2 ATR.
- One trade per session.
- No new entries after 14:30 IST.
- Square off by 15:15 IST.
- Risk budget defaults to 0.5% of available capital.
- Slippage and round-trip costs are included in the research configuration.

## Validation pipeline

```text
Dhan historical data
        ↓
Data-quality checks
        ↓
5-year historical test
        ↓
Chronological 60/20/20 split
        ↓
Walk-forward checks
        ↓
Out-of-sample test
        ↓
Live-market shadow/paper test
        ↓
Fixed-contract validation
        ↓
Promotion gate
        ↓
Only then: Dhan live execution review
```

## Hard promotion gates

A candidate is rejected if any mandatory gate fails.

### Historical

- At least 250 trades.
- Profit factor >= 1.25.
- Positive expectancy.
- Maximum drawdown <= 12%.
- At least 4 positive calendar years in the five-year sample.
- Positive out-of-sample test return.

### Live paper/shadow

- At least 60 trading days.
- Profit factor >= 1.15.
- Positive expectancy.
- Positive net P&L after measured execution costs.

### Data/execution

- No missing/duplicated market bars in the tested sessions beyond an explicitly accepted threshold.
- No look-ahead leakage.
- Entry is evaluated on a completed bar and filled on the next bar in historical simulation.
- Stop/target handling is conservative when both are touched inside one candle.
- The actual option/futures contract used for live paper trading must be validated; a synthetic/rolling research series alone cannot unlock live money.

## Dhan data

Dhan currently documents up to five years of minute-level intraday OHLC/OI/volume data, with a maximum 90-day polling window per request, so the research runner chunks the requested period and stores the results locally. Dhan also documents five years of expired-options rolling data with IV, OI, volume, OHLC and spot information. The rolling-options dataset is useful for research, but it is not by itself sufficient to approve live execution of a specific historical contract.

## Real-money rule

`LIVE` remains locked unless every promotion gate passes. A profitable backtest alone is never sufficient.
