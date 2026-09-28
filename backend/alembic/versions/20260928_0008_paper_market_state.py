"""Persist paper market indicator history.

Revision ID: 20260928_0008
Revises: 20260928_0007
"""
from alembic import op
import sqlalchemy as sa

revision = "20260928_0008"
down_revision = "20260928_0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "paper_market_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session", sa.String(40), nullable=False),
        sa.Column("symbol", sa.String(30), nullable=False),
        sa.Column("interval", sa.String(10), nullable=False),
        sa.Column("strategy_version", sa.String(10), nullable=False, server_default="V1"),
        sa.Column("state_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "session", "symbol", "interval", "strategy_version", name="uq_paper_market_state"),
    )
    op.create_index("ix_paper_market_states_id", "paper_market_states", ["id"])
    op.create_index("ix_paper_market_states_user_id", "paper_market_states", ["user_id"])
    op.create_index("ix_paper_market_states_symbol", "paper_market_states", ["symbol"])


def downgrade():
    op.drop_table("paper_market_states")
