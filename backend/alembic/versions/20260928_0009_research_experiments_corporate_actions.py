"""Research experiment lineage and corporate actions.
Revision ID: 20260928_0009
Revises: 20260928_0008
"""
from alembic import op
import sqlalchemy as sa
revision="20260928_0009"; down_revision="20260928_0008"; branch_labels=None; depends_on=None
def upgrade():
    op.create_table("research_experiments",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("user_id",sa.Integer(),nullable=False,index=True),
        sa.Column("experiment_key",sa.String(120),nullable=False),
        sa.Column("dataset_id",sa.String(200),nullable=False),
        sa.Column("strategy_version",sa.String(40),nullable=False),
        sa.Column("parameters_json",sa.Text(),nullable=False),
        sa.Column("result_json",sa.Text(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("user_id","experiment_key",name="uq_research_experiment_user_key"))
    op.create_index("ix_research_experiments_user_id","research_experiments",["user_id"])
    op.create_table("corporate_actions",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("symbol",sa.String(30),nullable=False,index=True),
        sa.Column("action_date",sa.Date(),nullable=False,index=True),
        sa.Column("action_type",sa.String(30),nullable=False),
        sa.Column("factor",sa.Numeric(18,8),nullable=False),
        sa.Column("source",sa.String(80),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("symbol","action_date","action_type","factor","source",name="uq_corporate_action"))
    op.create_index("ix_corporate_actions_symbol","corporate_actions",["symbol"])
    op.create_index("ix_corporate_actions_action_date","corporate_actions",["action_date"])
def downgrade():
    op.drop_table("corporate_actions"); op.drop_table("research_experiments")
