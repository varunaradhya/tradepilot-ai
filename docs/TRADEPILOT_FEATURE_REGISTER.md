[object Object]

## 2026-10-01 — CI hardening
- CI JWT test/deployment placeholders now meet the HS256 minimum recommended key length, removing an avoidable security warning from automated verification.


## 2026-10-01 — Recovery validation
- PostgreSQL backup/restore CI coverage is now end-to-end: backup creation, dedicated restore, restored-row verification, Alembic upgrade on the restored database, and FastAPI `/health` + `/ready` smoke tests.
- CI release gate passed with all required jobs green on run #1781.
