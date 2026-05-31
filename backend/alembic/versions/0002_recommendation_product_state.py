"""recommendation product state

Revision ID: 0002_rec_state
Revises: 0001_initial_cfo_os
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_rec_state"
down_revision = "0001_initial_cfo_os"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("recommendations") as batch:
        batch.add_column(sa.Column("user_type", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("stable_key", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch.add_column(sa.Column("impact_metric", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("primary_cta", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("secondary_cta", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("audit_log_id", sa.String(length=36), nullable=True))
        batch.create_foreign_key("fk_recommendations_audit_log_id_audit_logs", "audit_logs", ["audit_log_id"], ["id"])
    op.create_index("ix_recommendations_org_key", "recommendations", ["organization_id", "stable_key"])
    op.execute("UPDATE recommendations SET status = 'active' WHERE status = 'open'")


def downgrade() -> None:
    op.execute("UPDATE recommendations SET status = 'open' WHERE status = 'active'")
    op.drop_index("ix_recommendations_org_key", table_name="recommendations")
    with op.batch_alter_table("recommendations") as batch:
        batch.drop_constraint("fk_recommendations_audit_log_id_audit_logs", type_="foreignkey")
        batch.drop_column("audit_log_id")
        batch.drop_column("secondary_cta")
        batch.drop_column("primary_cta")
        batch.drop_column("impact_metric")
        batch.drop_column("description")
        batch.drop_column("stable_key")
        batch.drop_column("user_type")
