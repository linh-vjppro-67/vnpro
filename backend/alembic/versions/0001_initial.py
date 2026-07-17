"""initial schema
Revision ID: 0001
Revises:
Create Date: 2026-07-11
"""
from alembic import op
from app.db.base import Base
from app import models  # noqa: F401

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade():
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
