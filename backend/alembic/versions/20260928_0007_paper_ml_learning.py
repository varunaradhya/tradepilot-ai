"""paper ML learning lifecycle

Revision ID: 20260928_0007
Revises: 20260828_0006
"""
from alembic import op
import sqlalchemy as sa


revision = "20260928_0007"
down_revision = "20260828_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_trade_learning_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(30), nullable=False),
        sa.Column("session", sa.String(40), nullable=False),
        sa.Column("strategy_version", sa.String(20), nullable=False),
        sa.Column("model_version", sa.String(20), nullable=False, server_default="RULES_V1"),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("features_json", sa.Text(), nullable=False),
        sa.Column("label", sa.Integer(), nullable=False),
        sa.Column("pnl", sa.Float(), nullable=False),
        sa.Column("r_multiple", sa.Float(), nullable=False),
        sa.Column("exit_reason", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "fingerprint", name="uq_paper_learning_event"),
    )
    op.create_index("ix_paper_trade_learning_events_user_id", "paper_trade_learning_events", ["user_id"])
    op.create_index("ix_paper_trade_learning_events_symbol", "paper_trade_learning_events", ["symbol"])
    op.create_index("ix_paper_trade_learning_events_session", "paper_trade_learning_events", ["session"])
    op.create_index("ix_paper_trade_learning_events_strategy_version", "paper_trade_learning_events", ["strategy_version"])

    op.create_table(
        "paper_ml_models",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("strategy_version", sa.String(20), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("algorithm", sa.String(40), nullable=False),
        sa.Column("feature_names_json", sa.Text(), nullable=False),
        sa.Column("model_json", sa.Text(), nullable=False),
        sa.Column("metrics_json", sa.Text(), nullable=False),
        sa.Column("training_samples", sa.Integer(), nullable=False),
        sa.Column("validated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "strategy_version", "version", name="uq_paper_ml_model"),
    )
    op.create_index("ix_paper_ml_models_user_id", "paper_ml_models", ["user_id"])
    op.create_index("ix_paper_ml_models_strategy_version", "paper_ml_models", ["strategy_version"])

    op.create_table(
        "paper_ml_deployments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("strategy_version", sa.String(20), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False, server_default="SHADOW"),
        sa.Column("model_id", sa.Integer(), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=False, server_default="0.60"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "strategy_version", name="uq_paper_ml_deployment"),
    )
    op.create_index("ix_paper_ml_deployments_user_id", "paper_ml_deployments", ["user_id"])
    op.create_index("ix_paper_ml_deployments_strategy_version", "paper_ml_deployments", ["strategy_version"])

    op.create_table(
        "paper_ml_predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(30), nullable=False),
        sa.Column("strategy_version", sa.String(20), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("features_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_paper_ml_predictions_user_id", "paper_ml_predictions", ["user_id"])
    op.create_index("ix_paper_ml_predictions_model_id", "paper_ml_predictions", ["model_id"])
    op.create_index("ix_paper_ml_predictions_symbol", "paper_ml_predictions", ["symbol"])
    op.create_index("ix_paper_ml_predictions_strategy_version", "paper_ml_predictions", ["strategy_version"])


def downgrade() -> None:
    op.drop_table("paper_ml_predictions")
    op.drop_table("paper_ml_deployments")
    op.drop_table("paper_ml_models")
    op.drop_table("paper_trade_learning_events")
