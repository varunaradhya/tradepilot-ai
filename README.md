# TradePilot AI

TradePilot AI is a risk-first stock research, strategy validation and paper-trading platform built for disciplined intraday experimentation.

## Current status

**V1 stabilization / paper-trading ready foundation**

The project currently includes:

- React + TypeScript + Tailwind frontend
- FastAPI + Python backend
- SQLAlchemy persistence
- SQLite for local development and PostgreSQL for cloud deployment
- Deterministic long-first intraday signal engine
- Position risk and sizing engine
- Central execution safety gate
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

## Safety boundary

TradePilot is intentionally **paper-first**.

Live order execution is disabled by the execution safety layer. Broker adapters may expose capabilities and paper workflows, but a real-money order must not be inferred from a successful paper decision.

The intended flow is:

```text
Market data
    -> signal
    -> strategy readiness
    -> position sizing
    -> paper risk guard
    -> execution safety gate
    -> paper trade
    -> performance evidence
```

A strategy should demonstrate sufficient historical robustness and real paper performance before any future live-execution review.

## Local development

### Backend

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
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

## Verification baseline

The latest local verification checkpoint is **368 backend tests passing** with a successful Vite production build. The latest GitHub Actions run also passed backend tests, frontend build, and Docker Compose validation. Always rerun the local test/build commands after pulling changes.

## Project structure

```text
tradepilot-ai/
├── backend/           FastAPI application, domain services and tests
├── frontend/          React/TypeScript application
├── docs/              Architecture and operational documentation
├── scripts/            Development/operations helpers
├── docker-compose.yml Local production-like stack
└── .github/workflows/ CI
```

## Important disclaimer

TradePilot is a software and research platform, not financial advice. Paper results and historical backtests do not guarantee future performance. Keep live execution disabled until the strategy, data quality, operational controls and broker integration have been independently reviewed.
