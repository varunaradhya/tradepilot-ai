from alembic import op
import sqlalchemy as sa

revision = "20260929_0013"
down_revision = "20260928_0012"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("paper_trades", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("learning_event_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_paper_trades_learning_event",
            "paper_trade_learning_events",
            ["learning_event_id"],
            ["id"],
        )
        batch_op.create_index(
            "ix_paper_trades_learning_event_id",
            ["learning_event_id"],
        )


def downgrade():
    with op.batch_alter_table("paper_trades", recreate="always") as batch_op:
        batch_op.drop_index("ix_paper_trades_learning_event_id")
        batch_op.drop_constraint("fk_paper_trades_learning_event", type_="foreignkey")
        batch_op.drop_column("learning_event_id")
