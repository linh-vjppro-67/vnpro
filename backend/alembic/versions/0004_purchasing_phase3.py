"""Purchasing workflow phase 3, immutable DDL.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def ts():
    return [sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False)]


def upgrade():
    op.add_column("products", sa.Column("reserved_quantity", sa.Integer(), nullable=False, server_default="0"))
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(220), nullable=False), sa.Column("tax_code", sa.String(30)),
        sa.Column("phone", sa.String(30)), sa.Column("email", sa.String(190)),
        sa.Column("address", sa.String(400)), sa.Column("contact_person", sa.String(160)), *ts(),
    )
    op.create_index("ix_suppliers_code", "suppliers", ["code"], unique=True)
    op.create_table(
        "purchase_requests",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(40), nullable=False),
        sa.Column("department", sa.String(100), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id")),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reason", sa.String(300)), sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id")), *ts(),
    )
    for name in ("code", "department", "status"):
        op.create_index(f"ix_purchase_requests_{name}", "purchase_requests", [name], unique=name == "code")
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(40), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("purchase_request_id", sa.Integer(), sa.ForeignKey("purchase_requests.id")),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("expected_delivery_date", sa.Date()),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")), *ts(),
    )
    for name in ("code", "supplier_id", "status"):
        op.create_index(f"ix_purchase_orders_{name}", "purchase_orders", [name], unique=name == "code")
    op.create_table(
        "purchase_order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("purchase_order_id", sa.Integer(), sa.ForeignKey("purchase_orders.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False, server_default="0"),
    )
    op.create_index("ix_purchase_order_items_purchase_order_id", "purchase_order_items", ["purchase_order_id"])
    op.create_table(
        "stock_reservations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("sales_order_id", sa.Integer(), sa.ForeignKey("sales_orders.id")),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id")),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="RESERVED"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")), *ts(),
    )
    op.create_index("ix_stock_reservations_product_id", "stock_reservations", ["product_id"])
    op.create_index("ix_stock_reservations_status", "stock_reservations", ["status"])


def downgrade():
    for table in ["stock_reservations", "purchase_order_items", "purchase_orders", "purchase_requests", "suppliers"]:
        op.drop_table(table)
    op.drop_column("products", "reserved_quantity")
