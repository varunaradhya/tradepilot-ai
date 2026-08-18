"""Persist strategy authorization used by paper trading.

Revision ID: 20260818_0002
Revises: 20260815_0001
"""

from alembic import op
import sqlalchemy as sa

revision = "20260818_0002"
down_revision = "20260815_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "strategy_paper_authorizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("interval", sa.String(length=10), nullable=False),
        sa.Column("strategy_version", sa.String(length=10), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="AUTHORIZED"),
        sa.Column("evidence_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "user_id", "symbol", "interval", "strategy_version",
            name="uq_paper_auth_user_strategy",
        ),
    )
    op.create_index("ix_strategy_paper_authorizations_id", "strategy_paper_authorizations", ["id"], unique=False)
    op.create_index("ix_strategy_paper_authorizations_user_id", "strategy_paper_authorizations", ["user_id"], unique=False)
    op.create_index("ix_strategy_paper_authorizations_symbol", "strategy_paper_authorizations", ["symbol"], unique=False)
    op.create_index("ix_strategy_paper_authorizations_fingerprint", "strategy_paper_authorizations", ["fingerprint"], unique=False)
    op.create_index("ix_strategy_paper_authorizations_status", "strategy_paper_authorizations", ["status"], unique=False)


def downgrade():
    op.drop_table("strategy_paper_authorizations")
