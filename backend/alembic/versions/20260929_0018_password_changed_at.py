"""Track password changes for token invalidation.

Revision ID: 20260929_0018
Revises: 20260929_0017
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

revision = "20260929_0018"
down_revision = "20260929_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "password_changed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    # Existing users are treated as having changed their password at migration
    # time so previously issued credentials are not silently preserved.
    bind = op.get_bind()
    bind.execute(
        sa.text("UPDATE users SET password_changed_at = :ts WHERE password_changed_at IS NULL"),
        {"ts": datetime.now(timezone.utc)},
    )
    with op.batch_alter_table("users") as batch:
        batch.alter_column("password_changed_at", nullable=False)


def downgrade() -> None:
    op.drop_column("users", "password_changed_at")
