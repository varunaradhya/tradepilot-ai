"""Add option metadata to paper trades.

Revision ID: 20260821_0005
Revises: 20260818_0004
"""

from alembic import op
import sqlalchemy as sa

revision = "20260821_0005"
down_revision = "20260818_0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("paper_trades", sa.Column("asset_type", sa.String(length=10), nullable=False, server_default="EQUITY"))
    op.add_column("paper_trades", sa.Column("security_id", sa.String(length=30), nullable=True))
    op.add_column("paper_trades", sa.Column("exchange_segment", sa.String(length=20), nullable=True))
    op.add_column("paper_trades", sa.Column("underlying", sa.String(length=30), nullable=True))
    op.add_column("paper_trades", sa.Column("expiry", sa.String(length=10), nullable=True))
    op.add_column("paper_trades", sa.Column("strike", sa.Float(), nullable=True))
    op.add_column("paper_trades", sa.Column("option_type", sa.String(length=2), nullable=True))
    op.add_column("paper_trades", sa.Column("lot_size", sa.Integer(), nullable=True))
    op.create_index("ix_paper_trades_security_id", "paper_trades", ["security_id"], unique=False)


def downgrade():
    op.drop_index("ix_paper_trades_security_id", table_name="paper_trades")
    for column in ("lot_size", "option_type", "strike", "expiry", "underlying", "exchange_segment", "security_id", "asset_type"):
        op.drop_column("paper_trades", column)
