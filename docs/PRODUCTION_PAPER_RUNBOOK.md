# Production Paper-Trading Runbook

## Before market open

1. Confirm CI is green.
2. Confirm production backend health and readiness endpoints.
3. Confirm PostgreSQL connectivity and migrations.
4. Confirm Dhan credentials are present only in the deployment secret store.
5. Confirm Dhan read-only mode; no order-placement credential/path is enabled.
6. Confirm India timezone (`Asia/Kolkata`) and NSE session configuration.
7. Confirm market-data freshness threshold.
8. Confirm paper capital, allocation and max-position limits.

## During the session

- Watch the live-data indicator and last-update timestamp.
- A stale/missing/invalid LTP must fail closed.
- Record every paper entry and exit.
- Verify live gross and net P&L.
- Verify SL, target and trailing-stop movements.
- Investigate duplicate signals, duplicate ticks or unexpected exits immediately.

## End of session

1. Reconcile open/closed paper positions.
2. Reconcile gross P&L against trade records.
3. Reconcile itemized costs against the configured Indian cost model.
4. Confirm net P&L shown in UI equals persisted results.
5. Confirm no real broker order was submitted.
6. Archive the session evidence.

## Incident rules

- Dhan outage: stop opening new paper positions; do not invent prices.
- Stale LTP: stop price-triggered exits until fresh data resumes.
- Database outage: stop new paper entries; preserve safety over continuity.
- Unexpected restart: restore positions from persistence before resuming marks.
- Any real-order API call observed: immediately disable broker integration and investigate.
