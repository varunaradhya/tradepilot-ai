# TradePilot AI — Deployment Recovery Runbook

## Purpose

This runbook covers deployment-level checks that cannot be fully certified from source-code tests alone. CI performs an automated containerized restart and PostgreSQL outage/recovery drill; the same checks must be repeated in the real deployment environment before production use.

## Preconditions

- PostgreSQL backup destination is separate from the source database.
- Production secrets are supplied through the deployment secret manager and never committed to Git.
- Live broker execution remains hard-locked.
- A broker sandbox/test account is used for integration certification.

## Deployment startup

1. Validate the Compose configuration with production-like secret placeholders.
2. Start the stack.
3. Confirm database health.
4. Confirm backend `/health` returns HTTP 200 and `{"status":"healthy"}`.
5. Confirm backend `/ready` returns HTTP 200 and database availability.
6. Confirm the frontend is reachable.

Acceptance: all services are healthy and production does not use automatic schema creation.

## PostgreSQL backup/restore

1. Create a custom-format `pg_dump`.
2. Verify the dump with `pg_restore --list`.
3. Restore only into a dedicated restore database.
4. Verify a known probe record.
5. Run `alembic upgrade head` against the restored database.
6. Start the application against the restored database.
7. Verify `/health` and `/ready`.
8. Record backup timestamp, database version, migration head, restore duration, and result.

Acceptance: restored data is readable and the application reaches ready state.

## Application restart/recovery

1. Restart the backend service.
2. Wait for readiness.
3. Confirm database connectivity.
4. Confirm frontend availability.
5. Review application logs for startup or migration errors.

Acceptance: the service returns to ready state without manual schema repair.

## Database outage/recovery

1. Stop or isolate database connectivity in a controlled test environment.
2. Confirm `/ready` does not report database availability.
3. Restore database connectivity.
4. Confirm `/ready` returns to available state.
5. Check logs for repeated fatal loops or data corruption.

Acceptance: the application fails closed while the database is unavailable and recovers after connectivity returns.

## Broker sandbox certification

Before any live broker connection:

- Validate credential loading from the secret manager.
- Authenticate to the broker sandbox.
- Verify account identity and permissions.
- Submit only a sandbox/test order.
- Verify idempotency for repeated client intent.
- Verify rejection handling does not consume the retry key.
- Verify timeout/error handling does not create an unconfirmed duplicate.
- Reconcile broker order state against the TradePilot paper/execution ledger.
- Confirm live execution remains disabled.

Acceptance: all sandbox scenarios are reproducible and reconciled.

## Network/TLS failure drills

In a controlled environment:

- Invalidate a test TLS certificate and verify connection failure is detected.
- Block broker/API egress temporarily and verify the application fails closed.
- Restore connectivity and verify recovery.
- Confirm no duplicate order is generated during timeout/retry scenarios.
- Confirm alerts are emitted for sustained dependency failure.

Do not perform destructive network tests against production without an approved change window.

## Monitoring and alerting

Minimum operational signals:

- backend health/readiness failure
- database connectivity failure
- repeated container restarts
- migration failure
- backup failure
- restore drill failure
- broker authentication failure
- broker timeout/rejection
- unexpected execution-state mismatch

Alerts should identify the service, environment, timestamp, dependency, and correlation/idempotency identifier where available.

## Production gate

Production live execution stays locked until:

- CI release gate is green.
- Real deployment backup/restore is successful.
- Real restart/recovery is successful.
- Broker sandbox certification is successful.
- TLS/network failure drills are successful.
- Monitoring/alerting has been observed end-to-end.
- Research data is certified with explicit corporate-action provenance.
