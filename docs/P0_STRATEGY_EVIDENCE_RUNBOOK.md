# P0 Strategy Evidence Runbook

## Purpose

This is the execution contract for proving the existing intraday strategy before monitored paper trading or any future live review.

## Strategy scope

- Indian/NSE equities
- Intraday only
- Existing strategy versions only; do not create a replacement strategy for this gate
- Parameters are fixed before validation/OOS evaluation
- Real-money execution remains disabled

## Evidence sequence

```text
Dataset contract
  -> data-quality validation
  -> multi-year baseline
  -> robustness / parameter sensitivity
  -> fixed-parameter walk-forward
  -> untouched OOS
  -> strategy qualification
  -> monitored paper trading
  -> paper-vs-backtest divergence gate
  -> readiness review
```

## Multi-year baseline requirements

Default research horizon is 2021-2025 unless the evidence contract is explicitly changed.

The dataset must:

- contain every required year
- contain sufficient trading sessions in every required year
- be chronological by session and timestamp
- contain no duplicate timestamps
- contain valid positive OHLC values
- have close inside the high/low range
- preserve the exact strategy version/configuration
- preserve execution assumptions
- record the dataset identity and strategy fingerprint

The implementation is intentionally fail-closed when the evidence sample is incomplete.

## Required evidence

For each year and for the untouched latest OOS year record:

- sessions
- bars
- trades
- win rate
- profit factor
- expectancy
- maximum drawdown
- return
- transaction-cost drag

Also record:

- strategy fingerprint
- strategy version
- brokerage/slippage/spread/impact assumptions
- dataset period
- dataset identity
- whether parameters were fixed before evaluation

## Walk-forward rules

- chronological windows only
- validation windows must not overlap
- train and validation must not share future observations
- parameters must not be tuned using validation/OOS results
- insufficient windows fail closed
- session boundaries must be respected for any OOS split

## Qualification rules

A positive total return is never sufficient.

Qualification must consider:

- minimum trade count
- positive expectancy
- profit factor
- drawdown
- stability across years/windows
- OOS performance
- regime stability
- parameter sensitivity
- realistic cost/slippage sensitivity
- evidence of overfitting

## Paper gate

A qualified strategy moves to paper only after the historical evidence is reproducible. Paper performance must then be compared against historical expectations.

Material degradation means **NOT READY**, regardless of whether the paper account is profitable in absolute terms.

## Important limitation

The repository contains the research engines and research-store interfaces, but historical market datasets are not committed to Git. Therefore GitHub CI can verify the evidence pipeline code and its safety gates, but it cannot truthfully claim a five-year market result without the actual dataset being available to the research runtime.

When the five-year dataset is mounted/provided, run the existing research pipeline with the exact configuration recorded in the resulting evidence report. Never fabricate or manually enter performance numbers into source code.
