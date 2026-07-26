"""VNPRO order-centric workflow, immutable DDL.

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def ts():
    return [sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False)]


def upgrade():
    op.create_table(
        "technical_surveys",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(40), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("location", sa.String(300)), sa.Column("requirements", sa.Text(), nullable=False),
        sa.Column("current_state", sa.Text()), sa.Column("recommendation", sa.Text()),
        sa.Column("survey_date", sa.Date()), sa.Column("engineer_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), *ts(),
    )
    for name in ("code", "opportunity_id", "status"):
        op.create_index(f"ix_technical_surveys_{name}", "technical_surveys", [name], unique=name == "code")
    op.create_table(
        "solution_boms",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(40), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("survey_id", sa.Integer(), sa.ForeignKey("technical_surveys.id")),
        sa.Column("name", sa.String(250), nullable=False), sa.Column("scope", sa.Text()),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), *ts(),
    )
    for name in ("code", "opportunity_id", "status"):
        op.create_index(f"ix_solution_boms_{name}", "solution_boms", [name], unique=name == "code")
    op.create_table(
        "solution_bom_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bom_id", sa.Integer(), sa.ForeignKey("solution_boms.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id")),
        sa.Column("name", sa.String(250), nullable=False), sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit", sa.String(30), nullable=False, server_default="Cái"),
        sa.Column("estimated_cost", sa.Numeric(18, 2), nullable=False, server_default="0"), sa.Column("note", sa.Text()),
    )
    op.create_index("ix_solution_bom_items_bom_id", "solution_bom_items", ["bom_id"])
    op.create_table(
        "sales_order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sales_order_id", sa.Integer(), sa.ForeignKey("sales_orders.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("name", sa.String(250), nullable=False), sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("fulfilled_quantity", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_sales_order_items_sales_order_id", "sales_order_items", ["sales_order_id"])
    op.create_index("ix_sales_order_items_product_id", "sales_order_items", ["product_id"])
    op.create_table(
        "sales_invoices",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("invoice_no", sa.String(60), nullable=False),
        sa.Column("sales_order_id", sa.Integer(), sa.ForeignKey("sales_orders.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False), sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount_before_vat", sa.Numeric(18, 2), nullable=False),
        sa.Column("vat_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="ISSUED"),
        sa.Column("issued_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), *ts(),
    )
    op.create_index("ix_sales_invoices_invoice_no", "sales_invoices", ["invoice_no"], unique=True)
    op.create_index("ix_sales_invoices_sales_order_id", "sales_invoices", ["sales_order_id"])
    op.create_index("ix_sales_invoices_customer_id", "sales_invoices", ["customer_id"])
    op.create_index("ix_sales_invoices_status", "sales_invoices", ["status"])
    op.create_table(
        "payment_receipts",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(60), nullable=False),
        sa.Column("receivable_id", sa.Integer(), sa.ForeignKey("receivables.id"), nullable=False),
        sa.Column("sales_order_id", sa.Integer(), sa.ForeignKey("sales_orders.id")),
        sa.Column("received_date", sa.Date(), nullable=False), sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("method", sa.String(30), nullable=False, server_default="BANK_TRANSFER"),
        sa.Column("transaction_ref", sa.String(100)), sa.Column("note", sa.Text()),
        sa.Column("received_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), *ts(),
    )
    for name in ("code", "receivable_id", "sales_order_id"):
        op.create_index(f"ix_payment_receipts_{name}", "payment_receipts", [name], unique=name == "code")
    op.create_table(
        "order_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sales_order_id", sa.Integer(), sa.ForeignKey("sales_orders.id"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False), sa.Column("title", sa.String(200), nullable=False),
        sa.Column("details", sa.Text()), sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_order_events_sales_order_id", "order_events", ["sales_order_id"])
    op.create_index("ix_order_events_event_type", "order_events", ["event_type"])
    op.create_table(
        "expense_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expense_id", sa.Integer(), sa.ForeignKey("expenses.id"), nullable=False),
        sa.Column("paid_date", sa.Date(), nullable=False), sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("method", sa.String(30), nullable=False, server_default="BANK_TRANSFER"),
        sa.Column("transaction_ref", sa.String(100)),
        sa.Column("paid_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), *ts(),
    )
    op.create_index("ix_expense_payments_expense_id", "expense_payments", ["expense_id"])
    op.execute("UPDATE sales_orders SET status='IN_IMPLEMENTATION' WHERE status='IMPLEMENTING'")
    op.execute("UPDATE sales_orders SET status='WAITING_INVENTORY' WHERE status='CONFIRMED'")
    op.execute("UPDATE sales_orders SET status='CLOSED' WHERE status='COMPLETED'")


def downgrade():
    for table in [
        "expense_payments", "order_events", "payment_receipts", "sales_invoices",
        "sales_order_items", "solution_bom_items", "solution_boms", "technical_surveys",
    ]:
        op.drop_table(table)
