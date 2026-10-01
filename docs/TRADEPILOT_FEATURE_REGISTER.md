[object Object]

## 2026-10-01 — CI hardening
- CI JWT test/deployment placeholders now meet the HS256 minimum recommended key length, removing an avoidable security warning from automated verification.


## 2026-10-01 — Recovery validation
- PostgreSQL backup/restore CI coverage is now end-to-end: backup creation, dedicated restore, restored-row verification, Alembic upgrade on the restored database, and FastAPI `/health` + `/ready` smoke tests.
- CI release gate passed with all required jobs green on run #1781.


## 2026-10-01 — Product integration and premium workflow
- Premium presentation is now consolidated across the primary research, trading, portfolio, broker, transaction and F&O workspaces.
- Dashboard now exposes a direct workflow launchpad for Research → Strategy → Decision → Paper Trading.
- Portfolio remains the central capital/performance view, while Paper Trading remains the simulation execution layer.
- Broker connectivity remains separated from strategy authorization and live execution.
- Live broker order execution remains disabled.
