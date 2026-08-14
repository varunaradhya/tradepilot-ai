"""Initial TradePilot schema.

Revision ID: 20260815_0001
Revises:
Create Date: 2026-08-15
"""

from alembic import op
import sqlalchemy as sa

revision = "20260815_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "holdings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("average_buy_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_holdings_id", "holdings", ["id"], unique=False)
    op.create_index("ix_holdings_user_id", "holdings", ["user_id"], unique=False)
    op.create_index("ix_holdings_symbol", "holdings", ["symbol"], unique=False)

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("transaction_type", sa.String(length=10), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("transaction_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_transactions_id", "transactions", ["id"], unique=False)
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"], unique=False)
    op.create_index("ix_transactions_symbol", "transactions", ["symbol"], unique=False)

    op.create_table(
        "watchlist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "symbol", name="uq_watchlist_user_symbol"),
    )
    op.create_index("ix_watchlist_id", "watchlist", ["id"], unique=False)
    op.create_index("ix_watchlist_user_id", "watchlist", ["user_id"], unique=False)
    op.create_index("ix_watchlist_symbol", "watchlist", ["symbol"], unique=False)

    op.create_table(
        "broker_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("broker_name", sa.String(length=50), nullable=False),
        sa.Column("client_id", sa.String(length=100), nullable=False),
        sa.Column("encrypted_access_token", sa.Text(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(length=30), nullable=True),
        sa.Column("last_sync_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "broker_name", name="uq_broker_connection_user_broker"),
    )
    op.create_index("ix_broker_connections_id", "broker_connections", ["id"], unique=False)
    op.create_index("ix_broker_connections_user_id", "broker_connections", ["user_id"], unique=False)
    op.create_index("ix_broker_connections_broker_name", "broker_connections", ["broker_name"], unique=False)

    op.create_table(
        "ai_analysis_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("analysis_type", sa.String(length=30), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("signal", sa.String(length=10), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("context_version", sa.String(length=20), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_analysis_history_id", "ai_analysis_history", ["id"], unique=False)
    op.create_index("ix_ai_analysis_history_user_id", "ai_analysis_history", ["user_id"], unique=False)
    op.create_index("ix_ai_analysis_history_analysis_type", "ai_analysis_history", ["analysis_type"], unique=False)
    op.create_index("ix_ai_analysis_history_symbol", "ai_analysis_history", ["symbol"], unique=False)
    op.create_index("ix_ai_analysis_history_generated_at", "ai_analysis_history", ["generated_at"], unique=False)

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("severity", sa.String(length=10), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alerts_id", "alerts", ["id"], unique=False)
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"], unique=False)
    op.create_index("ix_alerts_type", "alerts", ["type"], unique=False)
    op.create_index("ix_alerts_symbol", "alerts", ["symbol"], unique=False)
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"], unique=False)


def downgrade():
    op.drop_table("alerts")
    op.drop_table("ai_analysis_history")
    op.drop_table("broker_connections")
    op.drop_table("watchlist")
    op.drop_table("transactions")
    op.drop_table("holdings")
    op.drop_table("users")
