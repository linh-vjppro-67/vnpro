"""purchasing workflow phase 3: suppliers, purchase requests/orders, stock reservations
Revision ID: 0004
Revises: 0003
Create Date: 2026-07-12
"""
import sqlalchemy as sa
from alembic import op
from app.db.base import Base
from app import models  # noqa: F401

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # See 0002 for why this column add is inspector-guarded: on a from-scratch database,
    # migration 0001 already creates `products` with reserved_quantity (current models.py),
    # so this only fires when upgrading a database created before this phase existed.
    Base.metadata.create_all(bind=bind)
    inspector = sa.inspect(bind)
    product_columns = {c["name"] for c in inspector.get_columns("products")}
    if "reserved_quantity" not in product_columns:
        op.add_column("products", sa.Column("reserved_quantity", sa.Integer(), nullable=True, server_default="0"))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    product_columns = {c["name"] for c in inspector.get_columns("products")}
    if "reserved_quantity" in product_columns:
        op.drop_column("products", "reserved_quantity")
    for table in ("stock_reservations", "purchase_order_items", "purchase_orders", "purchase_requests", "suppliers"):
        op.drop_table(table)
