# TradePilot AI

TradePilot AI is a risk-first stock research, strategy validation and paper-trading platform built for disciplined intraday experimentation.

## Project source of truth

Before starting feature development, read **[`docs/TRADEPILOT_FEATURE_REGISTER.md`](docs/TRADEPILOT_FEATURE_REGISTER.md)**. It is the project-wide feature and development register: implemented capabilities, intentional locks, environmental dependencies, backlog, architecture boundaries, definition of done, and change history.

## Current status

**V1 stabilization / paper-trading ready foundation — P5 production reliability foundation implemented**

The project includes a central execution safety gate, durable fail-closed kill switch, market-data freshness watchdog, operational audit retention, read-only broker sandbox certification, paper-risk controls, strategy qualification/readiness gates, NSE-first market data, multi-broker foundations, Docker deployment and GitHub Actions CI.

## Safety boundary

TradePilot is intentionally **paper-first**. Live order execution remains disabled by code. Broker adapters and sandbox certification cannot authorize real-money orders.

```text
Market data
    -> freshness watchdog
    -> signal
    -> strategy readiness
    -> position sizing
    -> paper risk guard
    -> execution safety gate
    -> paper trade
    -> performance evidence
    -> operational audit
```

The durable kill switch defaults to active. The trading API can activate it, but deliberately has no endpoint to deactivate it. Live execution remains locked.

## Operations endpoints

Authenticated endpoints include:

- `GET /api/v1/operations/safety`
- `GET /api/v1/operations/kill-switch`
- `POST /api/v1/operations/kill-switch/activate`
- `GET /api/v1/operations/audit-events`
- `GET /api/v1/operations/broker-sandbox/{broker}`

## Local development

### Backend

```powershell
cd backend
.\\.venv\\Scripts\\python.exe -m pytest
```

### Frontend

```powershell
cd frontend
npm.cmd run build
```

### Docker

```powershell
$env:POSTGRES_PASSWORD = "<strong-password>"
$env:TRADEPILOT_JWT_SECRET = "<strong-secret>"
$env:TRADEPILOT_BROKER_ENCRYPTION_KEY = "<strong-encryption-key>"
docker compose config
docker compose up --build
```

The backend exposes `/health` for liveness and `/ready` for database readiness.

## Verification

GitHub Actions is the source of truth for backend tests, frontend build and deployment-config validation. Always rerun the local test/build commands after pulling changes.

## Important disclaimer

TradePilot is a software and research platform, not financial advice. Paper results and historical backtests do not guarantee future performance. Keep live execution disabled until strategy, data quality, operational controls and broker integration have been independently reviewed.
