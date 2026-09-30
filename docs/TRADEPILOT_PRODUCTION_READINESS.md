# TradePilot AI — Production Readiness Runbook

This runbook records the checks that can be enforced in the repository and the checks that still require an actual deployment environment.

## Safety boundary

- Real-money/live broker execution remains disabled in code.
- F&O execution must remain paper-only.
- Production deployment must not be treated as trading certification.
- Market-data quality and corporate-action lineage must be certified separately before any research result is promoted.

## Deployment configuration

Required production environment variables:

- `POSTGRES_PASSWORD`
- `TRADEPILOT_JWT_SECRET`
- `TRADEPILOT_BROKER_ENCRYPTION_KEY`
- `TRADEPILOT_CORS_ORIGINS`

The production Compose file now fails closed when these are absent instead of falling back to a known database password or localhost CORS value.

## Startup and readiness

The backend container:

1. applies Alembic migrations,
2. starts FastAPI,
3. exposes `/health` for process health,
4. exposes `/ready` for database readiness.

Compose waits for PostgreSQL health before starting the backend and waits for backend readiness before starting the frontend.

## Backup / restore drill

For a deployment using the included Compose PostgreSQL service:

### Backup

```bash
mkdir -p backups
docker compose exec -T database pg_dump -U tradepilot -d tradepilot --format=custom > backups/tradepilot-$(date +%Y%m%d-%H%M%S).dump
```

### Restore drill

Use an isolated PostgreSQL instance/database for the first restore test. Do not restore over the production database during a drill.

```bash
cat backups/<backup-file>.dump | docker compose exec -T database pg_restore -U tradepilot -d tradepilot --clean --if-exists --no-owner
```

A successful command is not sufficient evidence by itself. The restored database must be checked for:

- Alembic head/version,
- user and ownership integrity,
- paper-trade/request idempotency records,
- ML lineage records,
- validation evidence,
- broker connection metadata,
- absence of live-execution enablement.

## Required runtime drills before production sign-off

These cannot be honestly marked complete from static repository inspection alone:

- PostgreSQL multi-worker concurrency under load.
- Restart during a paper mutation and recovery of PENDING requests.
- Database backup and restore.
- Secret rotation and token invalidation.
- Broker timeout/ambiguous-response handling.
- Market-data outage and stale-data handling.
- Migration upgrade from a representative existing database.
- Monitoring/alert delivery from a real deployment.
- Resource limits and container restart behavior.
- Recovery from a failed backend instance.

Record the date, environment, commit SHA, operator, commands, and observed result for every drill.

## Research certification gate

Do not promote a strategy/model based on the current broad Dhan-derived 5-minute dataset until:

1. the source timestamp contract is documented or the data is restricted to explicitly strict-valid sessions;
2. corporate-action adjustment state is source-backed and attached to the dataset lineage;
3. fees use an effective-date-appropriate schedule;
4. train/validation windows are chronological and non-overlapping;
5. no future information enters signal construction or execution;
6. real out-of-sample evidence is persisted and reproducible.

Current repository evidence still leaves corporate-action adjustment state **UNKNOWN** for the certified Dhan-derived sample. No profitability claim is made.

## CI gate

A release candidate is not considered verified unless the current commit has a completed GitHub Actions run with:

- backend tests,
- frontend build,
- Docker Compose validation,
- release gate success.

A missing, pending, cancelled, or unavailable run is **not** equivalent to pass.
