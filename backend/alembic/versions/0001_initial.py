"""Initial immutable schema.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(190), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("department", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(220), nullable=False),
        sa.Column("tax_code", sa.String(30)),
        sa.Column("phone", sa.String(30)),
        sa.Column("email", sa.String(190)),
        sa.Column("address", sa.String(400)),
        sa.Column("segment", sa.String(50), nullable=False, server_default="Doanh nghiệp"),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id")),
        *timestamps(),
    )
    op.create_index("ix_customers_code", "customers", ["code"], unique=True)
    op.create_index("ix_customers_name", "customers", ["name"])

    op.create_table(
        "opportunities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("title", sa.String(250), nullable=False),
        sa.Column("stage", sa.String(50), nullable=False, server_default="LEAD"),
        sa.Column("expected_value", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("probability", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("expected_close_date", sa.Date()),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id")),
        *timestamps(),
    )
    op.create_index("ix_opportunities_code", "opportunities", ["code"], unique=True)
    op.create_index("ix_opportunities_customer_id", "opportunities", ["customer_id"])
    op.create_index("ix_opportunities_stage", "opportunities", ["stage"])

    op.create_table(
        "sales_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id")),
        sa.Column("title", sa.String(250), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="DRAFT"),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("cost_estimate", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("payment_status", sa.String(50), nullable=False, server_default="UNPAID"),
        sa.Column("due_date", sa.Date()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        *timestamps(),
    )
    op.create_index("ix_sales_orders_code", "sales_orders", ["code"], unique=True)
    op.create_index("ix_sales_orders_customer_id", "sales_orders", ["customer_id"])
    op.create_index("ix_sales_orders_status", "sales_orders", ["status"])

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(250), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("sales_orders.id")),
        sa.Column("status", sa.String(50), nullable=False, server_default="PLANNING"),
        sa.Column("manager_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("start_date", sa.Date()),
        sa.Column("due_date", sa.Date()),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("budget_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("actual_cost", sa.Numeric(18, 2), nullable=False, server_default="0"),
        *timestamps(),
    )
    op.create_index("ix_projects_code", "projects", ["code"], unique=True)
    op.create_index("ix_projects_status", "projects", ["status"])

    op.create_table(
        "budgets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(220), nullable=False),
        sa.Column("department", sa.String(100), nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("spent_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(50), nullable=False, server_default="APPROVED"),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id")),
        *timestamps(),
    )
    op.create_index("ix_budgets_code", "budgets", ["code"], unique=True)
    op.create_index("ix_budgets_department", "budgets", ["department"])

    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("department", sa.String(100), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id")),
        sa.Column("status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id")),
        *timestamps(),
    )
    for name in ("code", "category", "department", "status"):
        op.create_index(f"ix_expenses_{name}", "expenses", [name], unique=name == "code")

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku", sa.String(60), nullable=False),
        sa.Column("name", sa.String(250), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False, server_default="Cái"),
        sa.Column("sale_price", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("cost_price", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("min_stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quantity_on_hand", sa.Integer(), nullable=False, server_default="0"),
        *timestamps(),
    )
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)
    op.create_index("ix_products_category", "products", ["category"])

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("movement_type", sa.String(30), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(100)),
        sa.Column("note", sa.String(300)),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        *timestamps(),
    )
    op.create_index("ix_stock_movements_product_id", "stock_movements", ["product_id"])

    op.create_table(
        "receivables",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("sales_orders.id")),
        sa.Column("invoice_no", sa.String(60), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("paid_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="OPEN"),
        *timestamps(),
    )
    op.create_index("ix_receivables_customer_id", "receivables", ["customer_id"])
    op.create_index("ix_receivables_status", "receivables", ["status"])

    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id")),
        sa.Column("subject", sa.String(250), nullable=False),
        sa.Column("priority", sa.String(30), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(50), nullable=False, server_default="OPEN"),
        sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("sla_due_at", sa.DateTime(timezone=True)),
        *timestamps(),
    )
    op.create_index("ix_support_tickets_code", "support_tickets", ["code"], unique=True)
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])

    op.create_table(
        "integration_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("system", sa.String(30), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("entity", sa.String(80), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_integration_logs_system", "integration_logs", ["system"])
    op.create_index("ix_integration_logs_status", "integration_logs", ["status"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.String(80)),
        sa.Column("details", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity"])


def downgrade():
    for table in [
        "audit_logs", "integration_logs", "support_tickets", "receivables",
        "stock_movements", "products", "expenses", "budgets", "projects",
        "sales_orders", "opportunities", "customers", "users",
    ]:
        op.drop_table(table)
