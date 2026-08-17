# Market Data Safety Contract

TradePilot treats market data as an input with explicit quality state, not as trusted truth.

## Intraday contract

A candle stream must satisfy:

- timestamps are monotonically increasing and unique;
- OHLC prices are finite and positive;
- `low <= open/close <= high`;
- candles are inside the Indian cash-market session (09:15–15:30 IST) on weekdays;
- missing intervals are measured only inside the same trading session;
- historical datasets are not marked stale from wall-clock age;
- live callers provide an explicit observation/reference time for stale-data checks.

A failed quality check must block downstream signal/execution decisions rather than silently repairing prices.

## Important distinction

Overnight, weekend, and session-boundary gaps are not missing intraday candles. Missing-bar detection must never infer bars between the last candle of one session and the first candle of the next.

## Live safety

The live pipeline should pass the latest observation time into the validator. If data exceeds the configured freshness budget, the decision engine must fail closed.

This contract intentionally does not hard-code the full NSE holiday calendar. A future calendar provider should supply exchange holidays rather than maintaining an error-prone static list inside validation logic.
