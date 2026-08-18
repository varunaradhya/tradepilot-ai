"""Persist simulation state so paper positions survive restarts.

Revision ID: 20260818_0004
Revises: 20260818_0003
"""

from alembic import op
import sqlalchemy as sa

revision = "20260818_0004"
down_revision = "20260818_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "paper_session_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("state_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_paper_session_state_user"),
    )
    op.create_index("ix_paper_session_states_id", "paper_session_states", ["id"], unique=False)
    op.create_index("ix_paper_session_states_user_id", "paper_session_states", ["user_id"], unique=False)


def downgrade():
    op.drop_table("paper_session_states")
