# TradePilot AI — Backtest Engine Audit

Date: 2026-09-30
Repository: varunaradhya/tradepilot-ai
Audit branch: certification-sync

## Scope

The audit covers the existing backend/app/services/backtest_service.py intraday research engine and its interaction with the strategy signal contract.

## Findings

| Area | Finding | Disposition |
|---|---|---|
| Signal execution | Completed-bar signals are queued and execute on the next bar open. | PASS — existing hardening |
| Final bar | A signal generated on the final bar is not executed without a following bar. | PASS — existing hardening |
| Stop/target ordering | Gap checks occur before intrabar stop/target checks; when both stop and target are inside one OHLC bar, stop is evaluated first. | PASS — conservative deterministic policy |
| Slippage | Buy and sell fills apply configured slippage. | PASS |
| Brokerage | Entry and exit brokerage are charged once per completed trade. | PASS |
| Position sizing | Sizing uses capital-at-risk and maximum capital fraction. | PASS — existing strategy contract |
| Daily loss | Daily loss halts new entries and clears pending signals. It does not force-liquidate an existing position. | ACCEPTED POLICY — new-entry gate |
| Session boundary | A pending signal could previously survive into the next session and execute at the next session open. | FIXED |
| Overnight exposure | A position could previously remain open across NSE sessions in the intraday engine. | FIXED by default; explicit opt-out exists |
| Indicator history | Indicators are calculated only from rows through the completed signal bar. | PASS by code inspection |
| Trailing stop | Current-bar high updates the trailing stop only after current-bar exit evaluation; the updated stop applies to later bars. | PASS by code inspection |
| Dataset ordering | When timestamps are supplied, the service rejects malformed, duplicate, or backward timestamps; upstream NSE session-grid certification remains authoritative. | PASS — entry-boundary guard added |
| Corporate actions | Fingerprinted research requires explicit corporate-action state. | PASS — existing lineage hardening |
| Dataset fingerprint | Fingerprint is propagated through lineage-backed research results. | PASS — existing lineage hardening |
| Multi-symbol contamination | When symbol metadata is supplied, the service requires a single consistent symbol across the input. | PASS — entry-boundary guard added |
| Statutory charges | The engine now supports an explicit/versioned India-equity fee schedule covering brokerage, exchange/IPFT, SEBI turnover, STT, stamp duty and GST, integrated into entry/exit cash and P&L. | PASS — integrated; historical effective-date schedule remains caller responsibility |

## Regression coverage added

Regression coverage verifies:

1. A signal created on the last bar of one session cannot execute on the next session.
2. An open intraday position is flattened at the previous session close when the next session begins.
3. Overnight carry is possible only through an explicit configuration opt-out.
4. Gap-through-stop exits use the reachable next-bar open rather than an unreachable stop price.
5. Same-bar stop/target ambiguity resolves conservatively to the stop.
6. Daily-loss breach halts additional entries.
7. Duplicate/backward timestamps, mixed symbols, malformed OHLC, and fee integration are rejected/verified.

## Research qualification boundary

This audit does not establish profitability or strategy quality. The real Dhan-derived five-minute dataset remains subject to the previously documented timestamp-quality and corporate-action-state blockers. No performance result is inferred from this code audit.

## Remaining backtest work

1. Add an India-equity fee model with separately auditable brokerage, exchange transaction charges, SEBI turnover fee, STT, stamp duty and GST inputs.
2. Add dataset-order/single-symbol/session assertions at the backtest entry boundary.
3. Add regression tests for gap-through-stop sizing, same-bar stop/target ambiguity, daily-loss semantics, and malformed/duplicate timestamps.
4. Keep real-data performance qualification blocked until dataset provenance and corporate-action state are established.

## 2026-09-30 — Final engineering audit

Current PR #46 HEAD `70a1ee5fbbbd9bd1a31c461c84a430dd30471985` was verified by GitHub Actions run **1649**. The backend suite passed (835 passed, 1 skipped, 102 warnings), together with frontend build, Docker Compose validation, and release-gate checks.

Additional code audit findings:
- Fee accounting is not double-counted: entry fees are charged when opening the position; exit fees are charged when closing it; the P&L field reports the combined fee impact without subtracting those fees from cash a second time.
- The legacy `brokerage_rate` override intentionally disables the other statutory fee components for backward-compatible callers/tests; the explicit fee schedule remains the preferred path.
- Session-boundary behavior, walk-forward non-overlap/exact-fit behavior, ML equal-timestamp ordering, and paper reconciliation open-trade scope have dedicated regression coverage.
- No change is warranted to the conservative stop-first same-bar policy or the default flat-at-session-end policy.

Research qualification remains blocked by source-backed corporate-action adjustment state and the documented historical timestamp/data-quality limitations. No profitability claim is established.
