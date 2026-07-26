"""CRM workflow phase 1, immutable DDL.

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def ts():
    return [sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False)]


def upgrade():
    op.add_column("opportunities", sa.Column("lead_id", sa.Integer()))
    op.create_index("ix_opportunities_lead_id", "opportunities", ["lead_id"])

    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("source", sa.String(50), nullable=False, server_default="OTHER"),
        sa.Column("company_name", sa.String(220), nullable=False),
        sa.Column("contact_name", sa.String(160), nullable=False),
        sa.Column("phone", sa.String(30)), sa.Column("email", sa.String(190)),
        sa.Column("need_summary", sa.Text()),
        sa.Column("potential_level", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("status", sa.String(30), nullable=False, server_default="NEW"),
        sa.Column("converted_to_opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id")),
        *ts(),
    )
    op.create_index("ix_leads_code", "leads", ["code"], unique=True)
    op.create_index("ix_leads_status", "leads", ["status"])

    op.create_table(
        "quotations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("payment_terms", sa.String(300)), sa.Column("warranty_terms", sa.String(300)),
        sa.Column("delivery_terms", sa.String(300)),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id")),
        *ts(),
    )
    for name in ("code", "opportunity_id", "customer_id", "status"):
        op.create_index(f"ix_quotations_{name}", "quotations", [name], unique=name == "code")

    op.create_table(
        "quotation_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quotation_id", sa.Integer(), sa.ForeignKey("quotations.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id")),
        sa.Column("name", sa.String(250), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=False, server_default="0"),
    )
    op.create_index("ix_quotation_items_quotation_id", "quotation_items", ["quotation_id"])

    op.create_table(
        "contracts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("quotation_id", sa.Integer(), sa.ForeignKey("quotations.id")),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id")),
        sa.Column("total_value", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("warranty_terms", sa.String(300)),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("signed_by", sa.String(160)),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("sales_order_id", sa.Integer()),
        *ts(),
    )
    op.create_index("ix_contracts_code", "contracts", ["code"], unique=True)
    op.create_index("ix_contracts_customer_id", "contracts", ["customer_id"])
    op.create_index("ix_contracts_status", "contracts", ["status"])

    with op.batch_alter_table("sales_orders") as batch:
        batch.add_column(sa.Column("contract_id", sa.Integer()))
        batch.create_foreign_key("fk_sales_orders_contract_id", "contracts", ["contract_id"], ["id"])

    op.create_table(
        "contract_payment_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("description", sa.String(250), nullable=False),
        sa.Column("due_condition", sa.String(250)), sa.Column("due_date", sa.Date()),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("invoiced", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_contract_payment_schedules_contract_id", "contract_payment_schedules", ["contract_id"])

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("approver_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("reason", sa.String(300)), sa.Column("decision_note", sa.String(300)),
        sa.Column("decided_at", sa.DateTime(timezone=True)), *ts(),
    )
    op.create_index("ix_approval_requests_entity", "approval_requests", ["entity_type", "entity_id"])
    op.create_index("ix_approval_requests_entity_type", "approval_requests", ["entity_type"])
    op.create_index("ix_approval_requests_entity_id", "approval_requests", ["entity_id"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])


def downgrade():
    for table in ["approval_requests", "contract_payment_schedules"]:
        op.drop_table(table)
    with op.batch_alter_table("sales_orders") as batch:
        batch.drop_constraint("fk_sales_orders_contract_id", type_="foreignkey")
        batch.drop_column("contract_id")
    for table in ["contracts", "quotation_items", "quotations", "leads"]:
        op.drop_table(table)
    op.drop_index("ix_opportunities_lead_id", table_name="opportunities")
    op.drop_column("opportunities", "lead_id")
