"""technical workflow phase 2: work orders, acceptance records
Revision ID: 0003
Revises: 0002
Create Date: 2026-07-12
"""
from alembic import op
from app.db.base import Base
from app import models  # noqa: F401

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # checkfirst=True (the default) skips tables that already exist, so this only creates the
    # new ones: work_orders, acceptance_records. No columns were added to existing tables in
    # this phase, so unlike 0002 there is no inspector-guarded ALTER TABLE step needed.
    Base.metadata.create_all(bind=bind)


def downgrade():
    for table in ("acceptance_records", "work_orders"):
        op.drop_table(table)
