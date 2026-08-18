"""Persist paper signal request idempotency keys and fingerprints.

Revision ID: 20260818_0003
Revises: 20260818_0002
"""

from alembic import op
import sqlalchemy as sa

revision = "20260818_0003"
down_revision = "20260818_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "paper_signal_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("strategy_version", sa.String(length=10), nullable=False),
        sa.Column("interval", sa.String(length=10), nullable=False, server_default="5"),
        sa.Column("session", sa.String(length=40), nullable=False),
        sa.Column("decision", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("response_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "request_id", name="uq_paper_signal_user_request"),
    )
    op.create_index("ix_paper_signal_requests_id", "paper_signal_requests", ["id"], unique=False)
    op.create_index("ix_paper_signal_requests_user_id", "paper_signal_requests", ["user_id"], unique=False)
    op.create_index("ix_paper_signal_requests_symbol", "paper_signal_requests", ["symbol"], unique=False)
    op.create_index("ix_paper_signal_requests_fingerprint", "paper_signal_requests", ["request_fingerprint"], unique=False)


def downgrade():
    op.drop_table("paper_signal_requests")
