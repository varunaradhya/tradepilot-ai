"""Persist dataset, strategy, and feature-schema lineage for ML evidence.

Revision ID: 20260929_0016
Revises: 20260929_0015
"""
from alembic import op
import sqlalchemy as sa

revision = "20260929_0016"
down_revision = "20260929_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "paper_trade_learning_events",
        sa.Column("dataset_fingerprint", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "paper_trade_learning_events",
        sa.Column("strategy_fingerprint", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_paper_learning_dataset_fingerprint",
        "paper_trade_learning_events",
        ["dataset_fingerprint"],
    )
    op.create_index(
        "ix_paper_learning_strategy_fingerprint",
        "paper_trade_learning_events",
        ["strategy_fingerprint"],
    )
    op.add_column(
        "paper_ml_models",
        sa.Column("dataset_fingerprint", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "paper_ml_models",
        sa.Column("strategy_fingerprint", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "paper_ml_models",
        sa.Column("feature_schema_fingerprint", sa.String(length=64), nullable=False, server_default=""),
    )
    op.create_index(
        "ix_paper_ml_models_dataset_fingerprint",
        "paper_ml_models",
        ["dataset_fingerprint"],
    )
    op.create_index(
        "ix_paper_ml_models_strategy_fingerprint",
        "paper_ml_models",
        ["strategy_fingerprint"],
    )


def downgrade() -> None:
    op.drop_index("ix_paper_ml_models_strategy_fingerprint", table_name="paper_ml_models")
    op.drop_index("ix_paper_ml_models_dataset_fingerprint", table_name="paper_ml_models")
    op.drop_column("paper_ml_models", "feature_schema_fingerprint")
    op.drop_column("paper_ml_models", "strategy_fingerprint")
    op.drop_column("paper_ml_models", "dataset_fingerprint")
    op.drop_index("ix_paper_learning_strategy_fingerprint", table_name="paper_trade_learning_events")
    op.drop_index("ix_paper_learning_dataset_fingerprint", table_name="paper_trade_learning_events")
    op.drop_column("paper_trade_learning_events", "strategy_fingerprint")
    op.drop_column("paper_trade_learning_events", "dataset_fingerprint")
