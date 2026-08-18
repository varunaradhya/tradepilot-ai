# TradePilot AI

TradePilot AI is a risk-first stock research, strategy validation and paper-trading platform built for disciplined intraday experimentation.

## Project source of truth

Before starting feature development, read **[`docs/TRADEPILOT_FEATURE_REGISTER.md`](docs/TRADEPILOT_FEATURE_REGISTER.md)**. It is the project-wide feature and development register: implemented capabilities, intentional locks, environmental dependencies, backlog, architecture boundaries, definition of done, and change history.

Any new feature, bug fix, research capability, UI workflow, safety control, broker capability, or deployment capability should update that register in the same change whenever practical. This prevents rebuilding functionality that already exists elsewhere in the repository.

## Current status

**V1 stabilization / paper-trading ready foundation — P5 production reliability foundation implemented**

The project currently includes:

- React + TypeScript + Tailwind frontend
- FastAPI + Python backend
- SQLAlchemy persistence
- SQLite for local development and PostgreSQL for cloud deployment
- Deterministic long-first intraday signal engine
- Position risk and sizing engine
- Central execution safety gate
- Durable fail-closed operational kill switch
- Market-data freshness watchdog with stale/future timestamp rejection
- Operational audit-event persistence and retention service
- Read-only broker sandbox certification contract
- Paper-risk controls for daily loss, trade count, loss streak and open positions
- Auditable paper trade-decision endpoint and command center
- Strategy qualification, robustness and walk-forward validation
- Strategy readiness / deployment gates
- Market-data quality checks
- Multi-broker abstraction for Dhan, Groww and Angel One foundations
- Docker Compose deployment stack
- GitHub Actions CI for backend tests and frontend production builds
- Runtime error boundary and resilient application navigation
- India/NSE-first market search and market-data presentation
- Server-side Indian equity validation for watchlist entries
- Keyboard-accessible stock search with resilient API error handling

## Safety boundary

TradePilot is intentionally **paper-first**.

Live order execution is disabled by the execution safety layer. Broker adapters may expose capabilities and paper workflows, but a real-money order must not be inferred from a successful paper decision.

The intended flow is:

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

The durable kill switch defaults to active and has no trading-API deactivation path. Broker sandbox certification is read-only and always reports live execution as disabled.

## Operations endpoints

Authenticated operational endpoints include:

- `GET /api/v1/operations/safety` — consolidated safety, session, market-data and paper-reconciliation status
- `GET /api/v1/operations/kill-switch` — durable kill-switch state
- `POST /api/v1/operations/kill-switch/activate` — activate the fail-safe kill switch
- `GET /api/v1/operations/audit-events` — recent operational evidence
- `GET /api/v1/operations/broker-sandbox/{broker}` — read-only adapter certification

There is deliberately **no API endpoint that deactivates the kill switch**, and no endpoint can enable live trading.

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

Set production secrets in the environment before starting the stack. Do not commit secrets.

```powershell
$env:POSTGRES_PASSWORD = "<strong-password>"
$env:TRADEPILOT_JWT_SECRET = "<strong-secret>"
$env:TRADEPILOT_BROKER_ENCRYPTION_KEY = "<strong-encryption-key>"
docker compose config
docker compose up --build
```

The backend exposes `/health` for liveness and `/ready` for database readiness.

## Verification

GitHub Actions is the source of truth for the backend test count, frontend build and deployment-config validation. Always rerun the local test/build commands after pulling changes.

## Project structure

```text
tradepilot-ai/
├── backend/           FastAPI application, domain services and tests
├── frontend/          React/TypeScript application
├── docs/              Architecture, feature register and operational documentation
├── scripts/            Development/operations helpers
├── docker-compose.yml Local production-like stack
└── .github/workflows/ CI
```

## Important disclaimer

TradePilot is a software and research platform, not financial advice. Paper results and historical backtests do not guarantee future performance. Keep live execution disabled until the strategy, data quality, operational controls and broker integration have been independently reviewed.
