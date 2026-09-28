from alembic import op
import sqlalchemy as sa
revision = "20260928_0011"
down_revision = "20260928_0010"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "paper_validation_symbols",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("validation_run", sa.String(64), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("bars", sa.Integer(), nullable=False),
        sa.Column("trades", sa.Integer(), nullable=False),
        sa.Column("net_pnl", sa.Float(), nullable=False),
        sa.Column("data_quality_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "validation_run", "session_date", "symbol", name="uq_paper_validation_symbol"),
    )
    op.create_index("ix_paper_validation_symbols_user_id", "paper_validation_symbols", ["user_id"])
    op.create_index("ix_paper_validation_symbols_validation_run", "paper_validation_symbols", ["validation_run"])
    op.create_index("ix_paper_validation_symbols_session_date", "paper_validation_symbols", ["session_date"])
    op.create_index("ix_paper_validation_symbols_symbol", "paper_validation_symbols", ["symbol"])

def downgrade():
    op.drop_table("paper_validation_symbols")
