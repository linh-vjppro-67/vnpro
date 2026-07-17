"""task management: company-wide work assignment (giao viec)
Revision ID: 0005
Revises: 0004
Create Date: 2026-07-17
"""
from alembic import op
from app.db.base import Base
from app import models  # noqa: F401

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # checkfirst=True (the default) skips tables that already exist; only creates `tasks`.
    Base.metadata.create_all(bind=bind)


def downgrade():
    op.drop_table("tasks")
