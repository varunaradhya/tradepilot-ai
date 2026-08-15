# Indian Historical Research Pipeline

TradePilot's research pipeline is intentionally separate from live trading.

## Universe

The instrument master is sourced from Dhan's public scrip master and filtered to `NSE_EQ` cash equities. Security IDs are resolved from the master rather than hard-coded.

## Data flow

```text
Dhan instrument master
        |
        v
NSE cash-equity universe
        |
        v
Security ID resolution
        |
        v
Dhan historical OHLCV
        |
        v
OHLC/data-quality validation
        |
        v
Local research dataset
        |
        v
Backtest / walk-forward / out-of-sample
```

## Daily data

Daily history can be requested from a symbol's inception. The protected research endpoint defaults to the latest five years and allows at most ten years in one request.

## Intraday data

Dhan supports 1, 5, 15, 25 and 60 minute intervals. Intraday history is fetched in 90-day chunks and should be persisted locally instead of repeatedly polling the provider.

## Data-quality gates

A dataset is not allowed into the backtest when it contains duplicate timestamps or non-increasing timestamps. OHLC prices must be positive and satisfy the high/low relationships. Missing volume is reported rather than silently fabricated.

## Research endpoint

After connecting Dhan, the backend exposes:

- `GET /api/v1/research/instruments?q=TCS` — authenticated Indian NSE equity search.
- `POST /api/v1/research/daily?symbol=TCS` — authenticated five-year daily dataset download.
- Optional `start` and `end` query parameters can bound the date range.

Datasets are stored under `backend/data/research/`, which is intentionally git-ignored.

## Research rules

1. Never use future candles to calculate a signal for an earlier candle.
2. Do not tune parameters on the final out-of-sample period.
3. Include realistic brokerage, taxes, slippage and liquidity constraints before judging performance.
4. Keep the raw provider response separate from derived features when we add long-term storage.
5. A high backtest return alone is not evidence of a deployable strategy.
