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
    # The original migration chain relied on application startup creating
    # paper_trades, but a fresh Alembic database must be self-contained.
    # Preserve compatibility with databases where the table already exists.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("paper_trades"):
        op.create_table(
            "paper_trades",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("symbol", sa.String(length=30), nullable=False),
            sa.Column("side", sa.String(length=10), nullable=False, server_default="BUY"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="OPEN"),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("entry_price", sa.Float(), nullable=False),
            sa.Column("stop_price", sa.Float(), nullable=False),
            sa.Column("target_price", sa.Float(), nullable=False),
            sa.Column("exit_price", sa.Float(), nullable=True),
            sa.Column("pnl", sa.Float(), nullable=False, server_default="0"),
            sa.Column("reason", sa.String(length=40), nullable=True),
            sa.Column("strategy_version", sa.String(length=10), nullable=False, server_default="V1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_paper_trades_id", "paper_trades", ["id"], unique=False)
        op.create_index("ix_paper_trades_user_id", "paper_trades", ["user_id"], unique=False)
        op.create_index("ix_paper_trades_symbol", "paper_trades", ["symbol"], unique=False)

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
