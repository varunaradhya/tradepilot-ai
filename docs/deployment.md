# Deployment notes

Local development uses `TRADEPILOT_DATABASE_URL=sqlite:///./tradepilot.db` and keeps `TRADEPILOT_AUTO_CREATE_SCHEMA=true`.

For a database that already exists, install Alembic, review the schema, then run `alembic stamp 20260815_0001`. New deployments should run `alembic upgrade head` with `TRADEPILOT_AUTO_CREATE_SCHEMA=false`. This baseline migration is intentionally non-destructive.

For PostgreSQL set `TRADEPILOT_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/tradepilot`; do not put the URL in source control.

Run alert evaluation from a worker or scheduler by calling `app.services.alert_scheduler.evaluate_user_alerts`. It is deterministic, does not place trades, and does not require an AI call beyond existing cached portfolio analysis.
