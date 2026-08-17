# TradePilot Phase 2 — Production Paper Trading Runbook

## Objective

Run TradePilot against production infrastructure and real NSE market data while keeping **real-money order execution disabled**.

The phase is complete only after one full NSE trading session has been observed and reconciled.

## Target architecture

- Frontend: Vercel or equivalent static hosting
- Backend: Render/Railway or equivalent container hosting
- Database: managed PostgreSQL
- Market data: Dhan read-only market data
- Execution: `SIMULATION_ONLY`

## Required secrets

Configure these in the hosting provider's secret/environment manager. Never commit them to GitHub and never expose broker credentials through Vite/frontend variables.

- `TRADEPILOT_DATABASE_URL`
- `TRADEPILOT_JWT_SECRET`
- `TRADEPILOT_BROKER_ENCRYPTION_KEY`
- `TRADEPILOT_CORS_ORIGINS`
- Dhan credentials required by the existing broker connection flow
- Optional AI variables only if AI-backed features are enabled

## Database migration

Production deployments must use PostgreSQL and Alembic migrations.

1. Provision PostgreSQL.
2. Set `TRADEPILOT_DATABASE_URL` to the managed PostgreSQL URL.
3. Set `TRADEPILOT_AUTO_CREATE_SCHEMA=false`.
4. Run `alembic upgrade head` before accepting traffic.
5. Confirm `/health` and `/ready`.

The backend container already runs `alembic upgrade head` before starting Uvicorn.

## Security checks

Before opening the frontend to users:

- Use a unique strong PostgreSQL password.
- Generate a high-entropy JWT secret.
- Generate the broker encryption key using a proper secret manager.
- Set CORS to the exact deployed frontend origin(s); do not use `*` in production.
- Confirm HTTPS is used for frontend, backend and broker callbacks where applicable.
- Confirm `.env` files and broker tokens are absent from the repository and frontend build output.
- Keep Dhan order APIs inaccessible to the paper runtime.

## Paper-mode checks

The production paper environment must satisfy all of these:

- Paper/simulation execution is the only enabled mode.
- Real order endpoints are not called by the paper workflow.
- Dhan is used only for account/market-data reads required by the paper workflow.
- Every simulated entry and exit is persisted.
- Every simulated trade records timestamp, symbol, entry/exit price, quantity, reason and P&L.
- Stale or missing market data must fail closed rather than create a simulated fill from invalid data.

## NSE session checks

Validate the application clock and timezone assumptions against `Asia/Kolkata`.

At minimum verify:

- pre-open handling does not create unintended entries;
- regular NSE session boundaries are correct;
- no new entries are generated after the configured cutoff;
- open paper positions are handled correctly at session close;
- holidays/weekends do not trigger false trading activity.

## Dhan validation

Connect one Dhan account in the application and verify:

1. Authentication/credential retrieval succeeds.
2. Account/portfolio read succeeds.
3. NSE equity instrument lookup succeeds.
4. Market LTP read succeeds for an NSE equity.
5. A paper position can consume the LTP.
6. Paper SL/target/exit logic updates from the market tick.
7. No order-placement API is invoked.
8. Broker errors are normalized and visible in logs.

## Full-session acceptance test

Run the application through one complete NSE trading session.

Capture:

- signals generated;
- signals rejected by risk/safety gates;
- paper entries;
- paper exits;
- LTP/data failures;
- stale-data incidents;
- broker/API errors;
- P&L and drawdown;
- application restarts or worker failures.

At the end of the session, reconcile the UI, database and broker market-data observations.

## Strategy promotion gate

Do not enable live orders because of a profitable day.

Review trade count, expectancy, profit factor, drawdown, robustness, walk-forward results, regime behaviour, data-quality incidents and operational failures. Continue paper trading until the evidence is sufficient.

## Rollback

If production paper trading behaves unexpectedly:

1. Disable the paper runtime/worker.
2. Keep the application in read-only mode.
3. Preserve logs and database records.
4. Identify whether the fault is strategy, data, broker integration or infrastructure.
5. Fix and rerun CI.
6. Resume paper trading only after the regression suite and deployment checks pass.

## Live trading policy

**Live execution remains disabled.** A software test pass is not sufficient to enable real-money orders. Live execution requires separate strategy, market-data, security, operational and broker review gates.
