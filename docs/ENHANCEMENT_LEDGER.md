# TradePilot AI — Enhancement & QA Ledger

Last updated: 2026-09-21

## Purpose

This is the canonical implementation ledger for TradePilot AI. Before changing trading, paper-execution, data, or qualification behavior:

1. Check whether the behavior is already implemented.
2. Reuse the existing implementation and tests.
3. If changing it, add a new ledger entry rather than creating a duplicate feature.
4. Record the code commit, tests/fixtures, evidence status, and remaining limitation.
5. Never mark a trading-safety item complete from synthetic data alone.

## Status legend

- **DONE** — implementation and intended regression coverage exist.
- **PARTIAL** — foundation exists but production/evidence validation remains.
- **BLOCKED** — required external evidence or environment is unavailable.
- **LOCKED** — intentionally disabled for safety.

## Current ledger

| Date | Area | Enhancement / fix | Evidence / test | Status | Commit |
|---|---|---|---|---|---|
| 2026-09-21 | F&O quotes | Autonomous entry requires executable ask; no LTP fallback | Missing-ask regression | DONE | 8358c473 |
| 2026-09-21 | F&O contract selection | Reject missing/invalid bid or ask | Missing bid/ask regression | DONE | dcfe8150 |
| 2026-09-21 | Historical replay | BUY uses ask and SELL uses bid only | LTP-only snapshot regression | DONE | 13581e0b |
| 2026-09-21 | Quote QA | Fixed bid/ask guard initialization regression | Focused dummy scenarios | DONE | e8a489db |
| 2026-09-21 | Paper marking | Missing executable bid no longer falls back to LTP | LTP-only live-quote regression | DONE | c0f5673e |
| 2026-09-21 | Quote regression | Added executable quote test coverage | LTP-only quote fixture | DONE | a435233c |
| 2026-09-21 | QA documentation | Recorded executable quote hardening | Status/QA docs | DONE | 5129736d |
| 2026-09-21 | F&O backtest | Added dummy next-bar, missing-bid and end-of-test liquidation cases | Deterministic fixtures | DONE | 72ef8382 |
| 2026-09-21 | Replay integrity | Reject non-numeric or non-increasing timestamps | Chronology fixtures | DONE | 9f1870c5 + fc7bdc90 |
| 2026-09-21 | QA documentation | Recorded replay chronology hardening and test limitations | Status update | DONE | 996ed93f |
| 2026-08-22 | Historical F&O execution | Enforce next-bar option fills and contract-time integrity | Historical backtest regressions | DONE | 614a44d1 |
| 2026-08-22 | Paper execution | Use executable option quotes for paper marking | Paper execution tests | DONE | 19766920 |
| 2026-08-21 | F&O risk | Size autonomous trades using net risk after costs | Risk-sizing tests | DONE | 967bc63e |
| 2026-08-21 | F&O P&L | Make option paper P&L net of trading costs | P&L tests | DONE | 899c12b9 |
| 2026-08-21 | Dhan auth | Persistent refresh-token sessions and automatic access refresh | Auth/session tests | DONE | 1e2913e4 + 518163de |
| 2026-08-18 | Paper safety | Paper state/risk boundaries, stale-session protection, symbol isolation | Adversarial paper-risk tests | DONE | ba46f607 |
| 2026-08-18 | Paper operations | Monitoring, reconciliation, scheduler and evidence gates | P1 paper operations suite | DONE | 24de9a47 |
| 2026-08-18 | Strategy evidence | Harden evidence/OOS integrity gates | Evidence regression suite | DONE | 9600f38 |
| 2026-08-18 | Strategy readiness | Fail-closed strategy readiness and cross-stock evidence gates | P3 adversarial tests | DONE | 11cb5c3c |
| 2026-08-18 | Release safety | Fail-closed production/release validation | Release gate suite | DONE | eba782c5 |

## Current open items

### P0 — Real historical F&O evidence
- **BLOCKED:** Real expired-option historical snapshots with timestamp-aligned executable bid/ask are still required.
- Dhan expired-option OHLC/OI/IV/volume/spot normalization exists, but it does not manufacture bid/ask and therefore cannot by itself qualify execution realism.
- Synthetic data may validate software behavior only; it cannot establish strategy performance.

### P0 — Paper execution resilience
- Explicit autonomous-session idempotency key.
- Restart reconciliation test.
- Duplicate scan/candle protection.
- Broker/data outage recovery and retry behavior.

### P0 — Risk hardening
- Daily loss limit.
- Portfolio/concentration limit.
- Consecutive-loss protection.
- Volatility-regime adjustment.
- Emergency kill switch integration test.

### P1 — Options realism
- Configurable spread-width stress gate.
- Minimum bid/ask quantity gate where provider data supports it.
- Circuit/price-band handling.
- Expiry-day behavior.
- Gap-through-stop test.
- Slippage stress scenarios.

### P1 — Qualification
- Real historical intraday options replay.
- Parameter contamination/reuse tests.
- Regime stability and parameter sensitivity.
- OOS qualification report.
- Minimum trade-count/statistical significance.
- Profit-factor/drawdown/expectancy stability.

## Non-repeat rules

Do not create another implementation for:

- completed-candle filtering;
- chronological candle ordering/deduplication;
- IST session handling;
- autonomous direction/CE/PE/strike/lot selection;
- cost-aware sizing and R:R;
- executable bid/ask boundaries;
- next-bar historical option fills;
- anti-look-ahead replay;
- persistent paper trade lifecycle;
- duplicate open-option protection;
- Dhan auth/refresh foundation;
- historical Dhan expired-option normalization.

Instead, extend the existing code and add a ledger entry.

## Verification policy

A synthetic fixture proves software behavior, not trading edge.

A feature can move from PARTIAL/BLOCKED to qualification-ready only when:
- relevant automated tests pass;
- real/replay evidence exists where required;
- no look-ahead or future-data contamination is present;
- costs/slippage are included where relevant;
- the result is recorded in this ledger and project status.

## Live trading

**LOCKED.** No qualification shortcut or synthetic test can unlock live broker execution.
