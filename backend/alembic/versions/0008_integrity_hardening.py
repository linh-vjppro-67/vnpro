"""integrity, audit and workflow hardening

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    op.execute("UPDATE sales_orders SET status='CLOSED' WHERE status='COMPLETED'")
    op.execute("UPDATE sales_orders SET payment_status='PARTIAL' WHERE payment_status='PARTIALLY_PAID'")
    op.execute("UPDATE expenses SET status='SUBMITTED' WHERE status='PENDING'")
    op.execute("UPDATE purchase_orders SET status='FULLY_RECEIVED' WHERE status='RECEIVED'")

    project_uniques = {x["name"] for x in inspector.get_unique_constraints("projects")}
    project_indexes = {x["name"] for x in inspector.get_indexes("projects")}
    if "uq_projects_order_id" not in project_uniques and "uq_projects_order_id" not in project_indexes:
        with op.batch_alter_table("projects") as batch:
            batch.create_unique_constraint("uq_projects_order_id", ["order_id"])
    with op.batch_alter_table("products") as batch:
        batch.create_check_constraint("ck_products_stock_nonnegative", "quantity_on_hand >= 0")
        batch.create_check_constraint("ck_products_reserved_nonnegative", "reserved_quantity >= 0")
        batch.create_check_constraint("ck_products_quarantine_nonnegative", "quarantine_quantity >= 0")
    with op.batch_alter_table("budgets") as batch:
        batch.create_check_constraint("ck_budgets_amounts_nonnegative", "amount >= 0 AND spent_amount >= 0 AND committed_amount >= 0")
    with op.batch_alter_table("receivables") as batch:
        batch.create_check_constraint("ck_receivables_payment_bounds", "amount >= 0 AND paid_amount >= 0 AND paid_amount <= amount")
        batch.create_check_constraint("ck_receivables_status", "status IN ('OPEN','PARTIAL','PAID','OVERDUE','CANCELLED')")
    with op.batch_alter_table("expenses") as batch:
        batch.create_check_constraint("ck_expenses_status", "status IN ('DRAFT','SUBMITTED','OVER_BUDGET','APPROVED','REJECTED','PAID','CANCELLED')")
    with op.batch_alter_table("projects") as batch:
        batch.create_check_constraint("ck_projects_status", "status IN ('PLANNING','IN_PROGRESS','WAITING_ACCEPTANCE','COMPLETED','CANCELLED')")
    with op.batch_alter_table("purchase_orders") as batch:
        batch.create_check_constraint("ck_purchase_orders_status", "status IN ('DRAFT','ORDERED','PARTIALLY_RECEIVED','FULLY_RECEIVED','CLOSED','CANCELLED')")
    with op.batch_alter_table("goods_receipts") as batch:
        batch.create_check_constraint("ck_goods_receipts_status", "status IN ('INSPECTED','POSTED','CANCELLED')")
    with op.batch_alter_table("sales_orders") as batch:
        batch.create_check_constraint(
            "ck_sales_orders_status",
            "status IN ('DRAFT','WAITING_INVENTORY','READY_FOR_DELIVERY','IN_IMPLEMENTATION','ACCEPTED','INVOICED','PARTIALLY_PAID','PAID','CLOSED','CANCELLED')",
        )
        batch.create_check_constraint("ck_sales_orders_payment_status", "payment_status IN ('UNPAID','PARTIAL','PAID')")
    item_product = next(x for x in inspector.get_columns("sales_order_items") if x["name"] == "product_id")
    if not item_product["nullable"]:
        with op.batch_alter_table("sales_order_items") as batch:
            batch.alter_column("product_id", existing_type=sa.Integer(), nullable=True)
    audit_columns = {x["name"] for x in inspector.get_columns("audit_logs")}
    audit_additions = [
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("old_values", sa.Text(), nullable=True),
        sa.Column("new_values", sa.Text(), nullable=True),
    ]
    missing_audit = [x for x in audit_additions if x.name not in audit_columns]
    if missing_audit:
        with op.batch_alter_table("audit_logs") as batch:
            for column in missing_audit:
                batch.add_column(column)
    acceptance_columns = {x["name"] for x in inspector.get_columns("acceptance_records")}
    acceptance_additions = [
        sa.Column("signed_date", sa.Date(), nullable=True),
        sa.Column("signed_file", sa.Text(), nullable=True),
        sa.Column("acceptance_type", sa.String(20), nullable=False, server_default="FULL"),
        sa.Column("checklist_result", sa.Text(), nullable=True),
    ]
    missing_acceptance = [x for x in acceptance_additions if x.name not in acceptance_columns]
    if missing_acceptance:
        with op.batch_alter_table("acceptance_records") as batch:
            for column in missing_acceptance:
                batch.add_column(column)
    user_columns = {x["name"] for x in inspector.get_columns("users")}
    user_additions = [
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
    ]
    missing_user = [x for x in user_additions if x.name not in user_columns]
    if missing_user:
        with op.batch_alter_table("users") as batch:
            for column in missing_user:
                batch.add_column(column)


def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_column("password_changed_at")
        batch.drop_column("locked_until")
        batch.drop_column("failed_login_attempts")
    with op.batch_alter_table("acceptance_records") as batch:
        batch.drop_column("checklist_result")
        batch.drop_column("acceptance_type")
        batch.drop_column("signed_file")
        batch.drop_column("signed_date")
    with op.batch_alter_table("sales_order_items") as batch:
        batch.alter_column("product_id", existing_type=sa.Integer(), nullable=False)
    with op.batch_alter_table("audit_logs") as batch:
        batch.drop_column("new_values")
        batch.drop_column("old_values")
        batch.drop_column("ip_address")
        batch.drop_column("request_id")
    with op.batch_alter_table("sales_orders") as batch:
        batch.drop_constraint("ck_sales_orders_payment_status", type_="check")
        batch.drop_constraint("ck_sales_orders_status", type_="check")
    with op.batch_alter_table("receivables") as batch:
        batch.drop_constraint("ck_receivables_status", type_="check")
        batch.drop_constraint("ck_receivables_payment_bounds", type_="check")
    with op.batch_alter_table("goods_receipts") as batch:
        batch.drop_constraint("ck_goods_receipts_status", type_="check")
    with op.batch_alter_table("purchase_orders") as batch:
        batch.drop_constraint("ck_purchase_orders_status", type_="check")
    with op.batch_alter_table("projects") as batch:
        batch.drop_constraint("ck_projects_status", type_="check")
    with op.batch_alter_table("expenses") as batch:
        batch.drop_constraint("ck_expenses_status", type_="check")
    with op.batch_alter_table("budgets") as batch:
        batch.drop_constraint("ck_budgets_amounts_nonnegative", type_="check")
    with op.batch_alter_table("products") as batch:
        batch.drop_constraint("ck_products_quarantine_nonnegative", type_="check")
        batch.drop_constraint("ck_products_reserved_nonnegative", type_="check")
        batch.drop_constraint("ck_products_stock_nonnegative", type_="check")
    with op.batch_alter_table("projects") as batch:
        batch.drop_constraint("uq_projects_order_id", type_="unique")
