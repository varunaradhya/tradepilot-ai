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
| Dataset ordering | The service does not independently perform complete timestamp-order/session-grid validation. | OPEN — upstream data contract |
| Corporate actions | Fingerprinted research requires explicit corporate-action state. | PASS — existing lineage hardening |
| Dataset fingerprint | Fingerprint is propagated through lineage-backed research results. | PASS — existing lineage hardening |
| Multi-symbol contamination | The service accepts a row sequence without independently asserting a single symbol. | OPEN — upstream dataset contract |
| Statutory charges | The engine models brokerage + slippage, not a complete NSE statutory fee schedule. | OPEN — implement configurable fee model |

## Regression coverage added

backend/tests/test_backtest_session_boundaries.py verifies:

1. A signal created on the last bar of one session cannot execute on the next session.
2. An open intraday position is flattened at the previous session close when the next session begins.
3. Overnight carry is possible only through an explicit configuration opt-out.

## Research qualification boundary

This audit does not establish profitability or strategy quality. The real Dhan-derived five-minute dataset remains subject to the previously documented timestamp-quality and corporate-action-state blockers. No performance result is inferred from this code audit.

## Remaining backtest work

1. Add an India-equity fee model with separately auditable brokerage, exchange transaction charges, SEBI turnover fee, STT, stamp duty and GST inputs.
2. Add dataset-order/single-symbol/session assertions at the backtest entry boundary.
3. Add regression tests for gap-through-stop sizing, same-bar stop/target ambiguity, daily-loss semantics, and malformed/duplicate timestamps.
4. Keep real-data performance qualification blocked until dataset provenance and corporate-action state are established.