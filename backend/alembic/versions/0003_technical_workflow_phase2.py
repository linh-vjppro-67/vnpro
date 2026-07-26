"""Technical workflow phase 2, immutable DDL.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def ts():
    return [sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False)]


def upgrade():
    op.create_table(
        "work_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("title", sa.String(250), nullable=False),
        sa.Column("location", sa.String(300)), sa.Column("scheduled_date", sa.Date()),
        sa.Column("technician_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("materials_needed", sa.Text()), sa.Column("checklist", sa.Text()),
        sa.Column("status", sa.String(30), nullable=False, server_default="PLANNED"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")), *ts(),
    )
    for name in ("code", "project_id", "status"):
        op.create_index(f"ix_work_orders_{name}", "work_orders", [name], unique=name == "code")
    op.create_table(
        "acceptance_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("work_order_id", sa.Integer(), sa.ForeignKey("work_orders.id"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("summary", sa.Text()), sa.Column("customer_signed_by", sa.String(160)),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id")), *ts(),
    )
    for name in ("code", "work_order_id", "project_id", "status"):
        op.create_index(f"ix_acceptance_records_{name}", "acceptance_records", [name], unique=name == "code")


def downgrade():
    op.drop_table("acceptance_records")
    op.drop_table("work_orders")
