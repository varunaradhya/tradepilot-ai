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


def downgrade():
    op.drop_table("paper_historical_runs")
