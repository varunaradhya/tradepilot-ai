# P8 — Release & Production Readiness

## Purpose
P8 converts the existing P1–P7 trading foundation into an auditable release process. It does not enable live orders.

## CI release gate
A release is valid only when all required GitHub Actions jobs succeed:

- backend compile
- backend pytest suite
- frontend production build
- Docker Compose configuration validation
- final `release-gate`

A missing workflow run is **not** a pass. A cancelled, skipped or failed required job blocks release.

## Production readiness checks

### Application
- `/health` responds successfully.
- `/ready` confirms database connectivity.
- Authentication/authorization remain enabled for protected APIs.
- No debug credentials or secrets are committed.

### Trading safety
- Execution mode remains `SIMULATION_ONLY`.
- Live-order capability remains disabled.
- Kill switch is fail-closed.
- Stale/future market data cannot drive paper execution.
- Paper reconciliation mismatch produces `HALT_AND_RECONCILE`.
- Strategy readiness remains evidence-gated.

### Broker boundary
Broker adapters may expose read-only/sandbox capabilities, but broker connectivity or certification must never change the live-order safety decision.

### Deployment
- Secrets are injected by the deployment environment, never committed.
- Database migrations/backups must be tested before production deployment.
- Container configuration must pass `docker compose config`.
- External metrics/alerts and provider sandbox credentials remain environmental gates.

## Release procedure

1. Open PR against `main`.
2. Wait for the complete Actions workflow.
3. Investigate every failure; never merge around a failing gate.
4. Confirm release-gate success.
5. Review the feature register.
6. Confirm live execution is still locked.
7. Merge only after all required checks are green.
8. Verify `/health` and `/ready` after deployment.
9. Start with paper trading and monitor reconciliation/data freshness.

## Live-trading gate
Live trading requires a separate explicit safety review and is not part of P8. Required future evidence includes real provider sandbox certification, production operational monitoring, failure-injection results, independent review and explicit business approval.
