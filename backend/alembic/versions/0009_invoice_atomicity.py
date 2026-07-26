"""Atomic invoice accumulator.

Revision ID: 0009
Revises: 0008
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "sales_orders",
        sa.Column("invoiced_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
    )
    op.execute("""
        UPDATE sales_orders
        SET invoiced_amount = COALESCE(
            (SELECT SUM(total_amount) FROM sales_invoices WHERE sales_invoices.sales_order_id = sales_orders.id), 0
        )
    """)


def downgrade():
    op.drop_column("sales_orders", "invoiced_amount")
