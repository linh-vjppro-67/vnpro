"""SRS production core

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    additions = {
        "budgets": [
            sa.Column("committed_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        ],
        "expenses": [
            sa.Column("budget_id", sa.Integer(), sa.ForeignKey("budgets.id", name="fk_expenses_budget_id"), nullable=True),
            sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id", name="fk_expenses_supplier_id"), nullable=True),
            sa.Column("attachment_refs", sa.Text(), nullable=True),
        ],
        "products": [
            sa.Column("quarantine_quantity", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("warehouse_location", sa.String(100), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        ],
        "quotations": [
            sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("valid_until", sa.Date(), nullable=True),
            sa.Column("currency", sa.String(10), nullable=False, server_default="VND"),
            sa.Column("estimated_cost", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("margin_percent", sa.Numeric(8, 2), nullable=False, server_default="0"),
            sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        ],
        "quotation_items": [
            sa.Column("unit", sa.String(30), nullable=False, server_default="Cái"),
            sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False, server_default="0"),
            sa.Column("estimated_cost", sa.Numeric(18, 2), nullable=False, server_default="0"),
        ],
        "contracts": [
            sa.Column("sign_date", sa.Date(), nullable=True),
            sa.Column("effective_date", sa.Date(), nullable=True),
            sa.Column("expiry_date", sa.Date(), nullable=True),
            sa.Column("delivery_scope", sa.Text(), nullable=True),
            sa.Column("customer_signer", sa.String(160), nullable=True),
            sa.Column("company_signer", sa.String(160), nullable=True),
            sa.Column("signed_file", sa.Text(), nullable=True),
        ],
        "support_tickets": [
            sa.Column("sales_order_id", sa.Integer(), sa.ForeignKey("sales_orders.id", name="fk_support_tickets_sales_order_id"), nullable=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", name="fk_support_tickets_product_id"), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolution", sa.Text(), nullable=True),
            sa.Column("warranty_status", sa.String(30), nullable=True),
        ],
    }
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table, columns in additions.items():
        existing = {column["name"] for column in inspector.get_columns(table)}
        missing = [column for column in columns if column.name not in existing]
        if missing:
            with op.batch_alter_table(table) as batch:
                for column in missing:
                    batch.add_column(column)
    timestamp_columns = lambda: [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]
    op.create_table(
        "approval_rules",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(160), nullable=False), sa.Column("min_amount", sa.Numeric(18, 2)),
        sa.Column("max_amount", sa.Numeric(18, 2)), sa.Column("max_discount_percent", sa.Numeric(8, 2)),
        sa.Column("min_margin_percent", sa.Numeric(8, 2)), sa.Column("over_budget", sa.Boolean()),
        sa.Column("approver_role", sa.String(50), nullable=False),
        sa.Column("step_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sla_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), *timestamp_columns(),
    )
    op.create_index("ix_approval_rules_document_type", "approval_rules", ["document_type"])
    op.create_table(
        "entity_attachments",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False), sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False), sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(100)), sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), *timestamp_columns(),
    )
    op.create_index("ix_entity_attachments_entity_type", "entity_attachments", ["entity_type"])
    op.create_index("ix_entity_attachments_entity_id", "entity_attachments", ["entity_id"])
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("role", sa.String(50)), sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False), sa.Column("entity_type", sa.String(50)),
        sa.Column("entity_id", sa.Integer()), sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        *timestamp_columns(),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_role", "notifications", ["role"])
    op.create_table(
        "warranty_profiles",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(40), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("sales_order_id", sa.Integer(), sa.ForeignKey("sales_orders.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id")), sa.Column("serial_no", sa.String(100)),
        sa.Column("start_date", sa.Date(), nullable=False), sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("coverage", sa.Text(), nullable=False), sa.Column("exclusions", sa.Text()),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"), *timestamp_columns(),
    )
    for name in ("code", "customer_id", "sales_order_id", "serial_no", "status"):
        op.create_index(f"ix_warranty_profiles_{name}", "warranty_profiles", [name], unique=name == "code")
    op.create_table(
        "collection_activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("receivable_id", sa.Integer(), sa.ForeignKey("receivables.id"), nullable=False),
        sa.Column("activity_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False), sa.Column("result", sa.Text(), nullable=False),
        sa.Column("promised_date", sa.Date()), sa.Column("promised_amount", sa.Numeric(18, 2)),
        sa.Column("next_follow_up", sa.Date()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), *timestamp_columns(),
    )
    op.create_index("ix_collection_activities_receivable_id", "collection_activities", ["receivable_id"])
    op.create_table(
        "goods_receipts",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(40), nullable=False),
        sa.Column("purchase_order_id", sa.Integer(), sa.ForeignKey("purchase_orders.id"), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("received_date", sa.Date(), nullable=False), sa.Column("delivery_note", sa.String(100)),
        sa.Column("document_checklist", sa.Text()), sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("posted_by", sa.Integer(), sa.ForeignKey("users.id")), *timestamp_columns(),
    )
    for name in ("code", "purchase_order_id", "status"):
        op.create_index(f"ix_goods_receipts_{name}", "goods_receipts", [name], unique=name == "code")
    op.create_table(
        "goods_receipt_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("goods_receipt_id", sa.Integer(), sa.ForeignKey("goods_receipts.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("received_quantity", sa.Integer(), nullable=False),
        sa.Column("accepted_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quarantine_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quality_note", sa.Text()),
    )
    op.create_index("ix_goods_receipt_lines_goods_receipt_id", "goods_receipt_lines", ["goods_receipt_id"])
    op.create_table(
        "ticket_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("support_tickets.id"), nullable=False),
        sa.Column("action", sa.String(40), nullable=False), sa.Column("note", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), *timestamp_columns(),
    )
    op.create_index("ix_ticket_events_ticket_id", "ticket_events", ["ticket_id"])
    op.create_table(
        "technical_requests",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(40), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id")),
        sa.Column("sales_order_id", sa.Integer(), sa.ForeignKey("sales_orders.id")),
        sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("support_tickets.id")),
        sa.Column("request_type", sa.String(30), nullable=False), sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("site_address", sa.String(500)), sa.Column("priority", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assignee_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("status", sa.String(30), nullable=False, server_default="NEW"), sa.Column("result_note", sa.Text()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), *timestamp_columns(),
    )
    for name in ("code", "opportunity_id", "sales_order_id", "ticket_id", "status"):
        op.create_index(f"ix_technical_requests_{name}", "technical_requests", [name], unique=name == "code")
    op.execute(sa.text("UPDATE users SET email = replace(email, '@proscale.vn', '@vnpro.vn') WHERE email LIKE '%@proscale.vn'"))
    op.execute(sa.text("UPDATE products SET sku = replace(sku, 'SCALE-PRO-', 'SCALE-VNPRO-') WHERE sku LIKE 'SCALE-PRO-%'"))


def downgrade():
    for table in [
        "ticket_events", "warranty_profiles", "collection_activities",
        "goods_receipt_lines", "goods_receipts", "notifications",
        "entity_attachments", "approval_rules", "technical_requests",
    ]:
        op.drop_table(table)
    with op.batch_alter_table("support_tickets") as batch:
        batch.drop_constraint("fk_support_tickets_product_id", type_="foreignkey")
        batch.drop_constraint("fk_support_tickets_sales_order_id", type_="foreignkey")
        for column in ["warranty_status", "resolution", "resolved_at", "first_response_at", "description", "product_id", "sales_order_id"]:
            batch.drop_column(column)
    with op.batch_alter_table("contracts") as batch:
        for column in ["signed_file", "company_signer", "customer_signer", "delivery_scope", "expiry_date", "effective_date", "sign_date"]:
            batch.drop_column(column)
    with op.batch_alter_table("quotation_items") as batch:
        for column in ["estimated_cost", "tax_rate", "unit"]:
            batch.drop_column(column)
    with op.batch_alter_table("quotations") as batch:
        for column in ["locked_at", "margin_percent", "estimated_cost", "currency", "valid_until", "version_no"]:
            batch.drop_column(column)
    with op.batch_alter_table("products") as batch:
        for column in ["is_active", "warehouse_location", "quarantine_quantity"]:
            batch.drop_column(column)
    with op.batch_alter_table("expenses") as batch:
        batch.drop_constraint("fk_expenses_supplier_id", type_="foreignkey")
        batch.drop_constraint("fk_expenses_budget_id", type_="foreignkey")
        for column in ["attachment_refs", "supplier_id", "budget_id"]:
            batch.drop_column(column)
    op.drop_column("budgets", "committed_amount")
