"""Add database idempotency for historical paper sessions.

Revision ID: 20260828_0006
Revises: 20260821_0005
"""

from alembic import op
import sqlalchemy as sa

revision = "20260828_0006"
down_revision = "20260821_0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "paper_historical_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("session", sa.String(length=10), nullable=False),
        sa.Column("interval", sa.String(length=10), nullable=False),
        sa.Column("strategy_version", sa.String(length=10), nullable=False, server_default="V1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "user_id",
            "symbol",
            "session",
            "interval",
            "strategy_version",
            name="uq_paper_historical_run",
        ),
    )
    op.create_index("ix_paper_historical_runs_id", "paper_historical_runs", ["id"], unique=False)
    op.create_index("ix_paper_historical_runs_user_id", "paper_historical_runs", ["user_id"], unique=False)
    op.create_index("ix_paper_historical_runs_symbol", "paper_historical_runs", ["symbol"], unique=False)

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT user_id, symbol, reason, strategy_version "
            "FROM paper_trades WHERE reason LIKE 'DHAN:%'"
        )
    ).mappings()
    seen = set()
    for row in rows:
        reason = row["reason"] or ""
        parts = reason.split(":")
        if len(parts) != 3 or not parts[1] or not parts[2]:
            continue
        key = (
            row["user_id"],
            row["symbol"],
            parts[1],
            parts[2],
            row["strategy_version"] or "V1",
        )
        if key in seen:
            continue
        seen.add(key)
        bind.execute(
            sa.text(
                "INSERT INTO paper_historical_runs "
                "(user_id, symbol, session, interval, strategy_version, created_at) "
                "VALUES (:user_id, :symbol, :session, :interval, :strategy_version, CURRENT_TIMESTAMP)"
            ),
            {
                "user_id": key[0],
                "symbol": key[1],
                "session": key[2],
                "interval": key[3],
                "strategy_version": key[4],
            },
        )


def downgrade():
    op.drop_table("paper_historical_runs")
