# TradePilot Algo Research Roadmap

## Current research stack

1. NSE equity instrument master and exact symbol resolution.
2. Dhan historical-data ingestion with validated local datasets.
3. Deterministic Strategy V1 and conservative backtesting.
4. Market-pressure and adversarial scenario checks.
5. Walk-forward window construction.
6. Research metrics: drawdown, Sharpe, Sortino, profit factor and losing streaks.
7. Indian-cost reference model for research reporting.
8. Market-regime classification: BULL, BEAR, SIDEWAYS, TRANSITION.

## Research rules

- Never use future bars to generate a signal.
- Keep validation periods strictly after their training periods.
- Do not tune parameters against the final out-of-sample period.
- Include realistic slippage and trading costs before judging performance.
- Report drawdown and losing streaks alongside return.
- A backtest is evidence, not a guarantee of future profitability.

## Next stage

Build a liquid NSE equity universe, populate five-year daily datasets incrementally, then run the baseline strategy across the universe. Compare results by market regime before changing parameters. Parameter optimization comes only after the baseline and out-of-sample protocol are stable.
