from alembic import op
import sqlalchemy as sa
revision = "20260928_0012"
down_revision = "20260928_0011"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "paper_validation_manifests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("validation_run", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("manifest_json", sa.Text(), nullable=False),
        sa.Column("root_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "validation_run", name="uq_paper_validation_manifest"),
    )
    op.create_index("ix_paper_validation_manifests_user_id", "paper_validation_manifests", ["user_id"])
    op.create_index("ix_paper_validation_manifests_validation_run", "paper_validation_manifests", ["validation_run"])

def downgrade():
    op.drop_table("paper_validation_manifests")
