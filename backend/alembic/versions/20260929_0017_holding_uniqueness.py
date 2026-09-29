"""Enforce one portfolio holding per user and symbol.

Revision ID: 20260929_0017
Revises: 20260929_0016
"""
from alembic import op

revision = "20260929_0017"
down_revision = "20260929_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fail closed if an existing database already contains duplicate
    # (user_id, symbol) rows. Silent consolidation could change portfolio
    # quantities/average prices without an explicit reconciliation decision.
    op.create_index(
        "uq_holdings_user_symbol",
        "holdings",
        ["user_id", "symbol"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_holdings_user_symbol", table_name="holdings")
