"""Persist the market-time timestamp used for ML feature ordering.

Revision ID: 20260929_0015
Revises: 20260929_0014
"""
from alembic import op
import sqlalchemy as sa

revision = "20260929_0015"
down_revision = "20260929_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "paper_trade_learning_events",
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_paper_trade_learning_events_event_at",
        "paper_trade_learning_events",
        ["event_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_paper_trade_learning_events_event_at",
        table_name="paper_trade_learning_events",
    )
    op.drop_column("paper_trade_learning_events", "event_at")
