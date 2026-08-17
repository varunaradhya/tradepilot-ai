# TradePilot AI — Phase 2 Production Paper-Trading Acceptance

## Scope

Phase 2 is complete only when the application can run an NSE-session paper trade using read-only Dhan market data, calculate Indian transaction costs, update live paper P&L, enforce exits, persist the lifecycle, and fail closed on unsafe data conditions.

## Gates

- [ ] CI green on the integration commit.
- [ ] Production PostgreSQL configured and migrations applied.
- [ ] Production secrets configured outside source control.
- [ ] Dhan read-only authentication succeeds.
- [ ] NSE instrument/security-ID mapping is verified.
- [ ] Live LTP is fresh and timestamped.
- [ ] Stale/missing/invalid LTP cannot trigger a paper fill or exit.
- [ ] Paper entry is persisted with symbol, quantity, entry price/time and allocation.
- [ ] Live mark-to-market P&L is visible in the UI.
- [ ] Net P&L includes brokerage, STT, exchange/transaction charges, SEBI/IPFT where applicable, GST and stamp duty as configured by the cost model.
- [ ] Stop-loss exit works.
- [ ] Target exit works.
- [ ] Trailing-stop exit works.
- [ ] Time/horizon fallback is distinguishable from price-triggered exits.
- [ ] Duplicate ticks/signals do not create duplicate positions.
- [ ] Backend restart does not lose persisted open paper positions.
- [ ] Dhan/API outage fails closed.
- [ ] Market-closed state is handled explicitly.
- [ ] End-of-session reconciliation matches persisted paper trades and displayed P&L.
- [ ] Real broker order placement remains disabled.

## Required evidence

For one controlled NSE paper session capture:

1. signal timestamp and instrument;
2. Dhan LTP timestamp/price samples;
3. paper entry record;
4. at least one live P&L update;
5. exit trigger and exit price/time;
6. gross P&L and itemized costs;
7. net P&L;
8. persisted trade record;
9. UI trade-history record;
10. confirmation that no broker order endpoint was called.

## Operational rule

Do not enable real-money order placement from this checklist. Phase 2 is a paper-trading/data-integrity gate only. Live execution requires a separate release decision and independent evidence review.
