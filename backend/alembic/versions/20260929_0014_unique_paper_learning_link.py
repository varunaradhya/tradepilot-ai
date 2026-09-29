from alembic import op

revision = "20260929_0014"
down_revision = "20260929_0013"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("ix_paper_trades_learning_event_id", table_name="paper_trades")
    op.create_index(
        "ix_paper_trades_learning_event_id",
        "paper_trades",
        ["learning_event_id"],
        unique=True,
    )


def downgrade():
    op.drop_index("ix_paper_trades_learning_event_id", table_name="paper_trades")
    op.create_index(
        "ix_paper_trades_learning_event_id",
        "paper_trades",
        ["learning_event_id"],
        unique=False,
    )
