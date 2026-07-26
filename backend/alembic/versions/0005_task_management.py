"""Task management, immutable DDL.

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(40), nullable=False),
        sa.Column("title", sa.String(250), nullable=False), sa.Column("description", sa.Text()),
        sa.Column("department", sa.String(100), nullable=False),
        sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("due_date", sa.Date()), sa.Column("status", sa.String(30), nullable=False, server_default="NEW"),
        sa.Column("progress_note", sa.Text()), sa.Column("confirmed_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name in ("code", "department", "assigned_to", "assigned_by", "status"):
        op.create_index(f"ix_tasks_{name}", "tasks", [name], unique=name == "code")


def downgrade():
    op.drop_table("tasks")
