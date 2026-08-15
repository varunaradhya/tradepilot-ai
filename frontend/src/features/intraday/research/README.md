# Intraday Research Workspace

This feature is the frontend contract/documentation for the Iteration 1 intraday research workspace. It is intentionally framework-agnostic until the existing frontend structure is inspected locally.

## Workspace sections
- Universe and symbol selection
- Benchmark context (NIFTY/BANKNIFTY)
- Strategy V1/V2 comparison
- Regime performance
- Time-of-day performance
- Slippage sensitivity
- Risk/readiness verdict
- Research run status and errors

## UX principles
- Trading information must remain readable before animation.
- Animations are short and state-driven; no continuous decorative motion.
- Respect `prefers-reduced-motion`.
- Research results must show assumptions and data coverage.
- Never display fabricated metrics when a dataset is missing.
