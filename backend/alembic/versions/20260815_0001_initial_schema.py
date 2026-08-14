"""Initial schema baseline.

Revision ID: 20260815_0001
Revises:
Create Date: 2026-08-15
"""

from alembic import op

revision = "20260815_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Existing local databases should be stamped with this baseline, not recreated.
    pass


def downgrade():
    pass
