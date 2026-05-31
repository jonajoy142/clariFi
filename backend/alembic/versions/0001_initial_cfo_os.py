"""initial cfo os schema

Revision ID: 0001_initial_cfo_os
Revises:
Create Date: 2026-05-31
"""

from alembic import op

from app.models.finance import Base

revision = "0001_initial_cfo_os"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
