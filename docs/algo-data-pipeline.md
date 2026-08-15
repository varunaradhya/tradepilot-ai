# Algo Research Data Pipeline

## Source

TradePilot uses DhanHQ historical chart APIs for authenticated research data. Daily candles are requested from `/charts/historical`; intraday candles use `/charts/intraday`.

Dhan's current API uses `securityId`, `exchangeSegment`, and `instrument`. For Indian cash equities the default research mapping is `NSE_EQ` + `EQUITY`.

## Intraday chunking

Dhan limits a single intraday historical request to 90 days. `dhan_historical_service.fetch_intraday_history` therefore splits a requested date range into non-overlapping 90-day windows, fetches each window, normalizes the responses, and combines them chronologically.

## Data-quality gate

Every dataset passes through `normalize_bars` and `validate_dataset` before it can enter a backtest.

The gate rejects or flags:

- missing/invalid timestamps
- non-positive OHLC prices
- impossible OHLC relationships
- duplicate timestamps
- non-increasing timestamps
- missing volume
- inconsistent provider response arrays

A failed quality gate must stop research ingestion rather than silently repairing financial data.

## Research rules

1. Store raw provider responses separately from normalized research bars when persistence is added.
2. Never use future bars while calculating a signal for an earlier bar.
3. Preserve the source security ID, segment, instrument and retrieval range as dataset metadata.
4. Keep an untouched out-of-sample period for final evaluation.
5. Include transaction costs and slippage in all strategy comparisons.
6. Do not optimize parameters against the final out-of-sample period.

## Next implementation stage

Add a local research-data store and Dhan instrument-master importer. The instrument master will map Indian symbols to Dhan security IDs before five-year downloads begin. After ingestion, run the same dataset through baseline Strategy V1 and walk-forward validation.
