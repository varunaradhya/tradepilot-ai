from alembic import op
import sqlalchemy as sa

revision = "20260929_0013"
down_revision = "20260928_0012"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "paper_trades",
        sa.Column("learning_event_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_paper_trades_learning_event",
        "paper_trades",
        "paper_trade_learning_events",
        ["learning_event_id"],
        ["id"],
    )
    op.create_index(
        "ix_paper_trades_learning_event_id",
        "paper_trades",
        ["learning_event_id"],
    )


def downgrade():
    op.drop_index("ix_paper_trades_learning_event_id", table_name="paper_trades")
    op.drop_constraint("fk_paper_trades_learning_event", "paper_trades", type_="foreignkey")
    op.drop_column("paper_trades", "learning_event_id")
