# TradePilot Algo Research Protocol

## Objective

Build a robust Indian-market strategy without assuming profitability in advance. No strategy is treated as production-ready because of a high historical return alone.

## Data rules

1. Normalize provider OHLCV into a common bar model.
2. Reject malformed OHLC relationships before backtesting.
3. Detect duplicate/non-increasing timestamps before a dataset is accepted.
4. Preserve missing-volume information instead of silently replacing it.
5. Keep the data source, symbol, interval and retrieval timestamp with every research dataset.
6. Account for corporate actions and instrument changes before comparing long historical periods.
7. Do not use future information when constructing signals or features.

## Validation sequence

1. Synthetic/adversarial scenarios.
2. Baseline historical backtest.
3. Walk-forward train/validation windows.
4. Untouched out-of-sample period.
5. Transaction-cost and slippage stress tests.
6. Parameter sensitivity tests.
7. Monte Carlo trade/order stress tests.
8. Paper trading.
9. Only after all gates pass, evaluate controlled live execution.

## Acceptance metrics

Evaluate return, CAGR, maximum drawdown, Sharpe, Sortino, profit factor, expectancy, win rate, losing streak, recovery time, exposure, turnover and stability across market regimes.

A strategy is rejected if performance depends on a narrow parameter choice, one market regime, unrealistic fills, unavailable historical data, or materially deteriorates after costs.

## Market-pressure / institutional proxies

Use observable proxies such as volume anomalies, delivery, open interest, price/OI relationships, breadth, sector relative strength, VWAP and legitimate exchange disclosures. These are evidence of market conditions, not proof that a specific participant manipulated a security.
