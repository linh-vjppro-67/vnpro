"""crm workflow phase 1: leads, quotations, contracts, approval requests
Revision ID: 0002
Revises: 0001
Create Date: 2026-07-11
"""
import sqlalchemy as sa
from alembic import op
from app.db.base import Base
from app import models  # noqa: F401

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # checkfirst=True (the default) skips tables that already exist, so this only creates the
    # new ones: leads, quotations, quotation_items, contracts, contract_payment_schedules,
    # approval_requests. create_all() never alters existing tables — BUT on a brand-new database
    # this is the first migration to run against the *current* models.py, so it also creates
    # opportunities/sales_orders already carrying lead_id/contract_id. The explicit column adds
    # below are therefore guarded by an inspector check: they only fire when upgrading a database
    # that ran migration 0001 before these columns existed.
    Base.metadata.create_all(bind=bind)
    inspector = sa.inspect(bind)

    opportunity_columns = {c["name"] for c in inspector.get_columns("opportunities")}
    if "lead_id" not in opportunity_columns:
        op.add_column("opportunities", sa.Column("lead_id", sa.Integer(), nullable=True))
        op.create_index("ix_opportunities_lead_id", "opportunities", ["lead_id"])

    sales_order_columns = {c["name"] for c in inspector.get_columns("sales_orders")}
    if "contract_id" not in sales_order_columns:
        op.add_column("sales_orders", sa.Column("contract_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_sales_orders_contract_id", "sales_orders", "contracts", ["contract_id"], ["id"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    sales_order_columns = {c["name"] for c in inspector.get_columns("sales_orders")}
    if "contract_id" in sales_order_columns:
        op.drop_constraint("fk_sales_orders_contract_id", "sales_orders", type_="foreignkey")
        op.drop_column("sales_orders", "contract_id")
    opportunity_columns = {c["name"] for c in inspector.get_columns("opportunities")}
    if "lead_id" in opportunity_columns:
        op.drop_index("ix_opportunities_lead_id", table_name="opportunities")
        op.drop_column("opportunities", "lead_id")
    for table in ("approval_requests", "contract_payment_schedules", "contracts", "quotation_items", "quotations", "leads"):
        op.drop_table(table)
