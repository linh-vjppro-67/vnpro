from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text, Integer, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(190), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), index=True)
    department: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(220), index=True)
    tax_code: Mapped[str | None] = mapped_column(String(30))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(190))
    address: Mapped[str | None] = mapped_column(String(400))
    segment: Mapped[str] = mapped_column(String(50), default="Doanh nghiệp")
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    owner: Mapped[User | None] = relationship()


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(50), default="OTHER")
    company_name: Mapped[str] = mapped_column(String(220))
    contact_name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(190))
    need_summary: Mapped[str | None] = mapped_column(Text)
    potential_level: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="NEW", index=True)
    converted_to_opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"))
    owner: Mapped[User | None] = relationship()


class Opportunity(Base, TimestampMixin):
    __tablename__ = "opportunities"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    title: Mapped[str] = mapped_column(String(250))
    stage: Mapped[str] = mapped_column(String(50), default="LEAD", index=True)
    expected_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    probability: Mapped[int] = mapped_column(Integer, default=10)
    expected_close_date: Mapped[date | None] = mapped_column(Date)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    # informational reverse pointer only (no FK): Lead.converted_to_opportunity_id already
    # FKs the other direction, and SQLite (used by tests via create_all) cannot add the
    # ALTER TABLE constraint needed to break a real mutual-FK cycle between these two tables.
    lead_id: Mapped[int | None] = mapped_column(Integer, index=True)
    customer: Mapped[Customer] = relationship()
    owner: Mapped[User | None] = relationship()


class SalesOrder(Base, TimestampMixin):
    __tablename__ = "sales_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"))
    contract_id: Mapped[int | None] = mapped_column(ForeignKey("contracts.id"))
    title: Mapped[str] = mapped_column(String(250))
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", index=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    cost_estimate: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    payment_status: Mapped[str] = mapped_column(String(50), default="UNPAID")
    invoiced_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    due_date: Mapped[date | None] = mapped_column(Date)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    customer: Mapped[Customer] = relationship()


class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("order_id", name="uq_projects_order_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(250))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("sales_orders.id"))
    status: Mapped[str] = mapped_column(String(50), default="PLANNING", index=True)
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    start_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    budget_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    customer: Mapped[Customer] = relationship()
    manager: Mapped[User | None] = relationship()


class WorkOrder(Base, TimestampMixin):
    __tablename__ = "work_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    title: Mapped[str] = mapped_column(String(250))
    location: Mapped[str | None] = mapped_column(String(300))
    scheduled_date: Mapped[date | None] = mapped_column(Date)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    materials_needed: Mapped[str | None] = mapped_column(Text)
    checklist: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="PLANNED", index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    project: Mapped[Project] = relationship()
    technician: Mapped[User | None] = relationship(foreign_keys=[technician_id])


class AcceptanceRecord(Base, TimestampMixin):
    __tablename__ = "acceptance_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    customer_signed_by: Mapped[str | None] = mapped_column(String(160))
    signed_date: Mapped[date | None] = mapped_column(Date)
    signed_file: Mapped[str | None] = mapped_column(Text)
    acceptance_type: Mapped[str] = mapped_column(String(20), default="FULL")
    checklist_result: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    work_order: Mapped[WorkOrder] = relationship()
    project: Mapped[Project] = relationship()


class Budget(Base, TimestampMixin):
    __tablename__ = "budgets"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(220))
    department: Mapped[str] = mapped_column(String(100), index=True)
    period: Mapped[str] = mapped_column(String(20))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    spent_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    committed_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    status: Mapped[str] = mapped_column(String(50), default="APPROVED")
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class Expense(Base, TimestampMixin):
    __tablename__ = "expenses"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(300))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    category: Mapped[str] = mapped_column(String(100), index=True)
    department: Mapped[str] = mapped_column(String(100), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", index=True)
    expense_date: Mapped[date] = mapped_column(Date, default=date.today)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    budget_id: Mapped[int | None] = mapped_column(ForeignKey("budgets.id"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    attachment_refs: Mapped[str | None] = mapped_column(Text)
    project: Mapped[Project | None] = relationship()


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(250))
    category: Mapped[str] = mapped_column(String(100), index=True)
    unit: Mapped[str] = mapped_column(String(30), default="Cái")
    sale_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    min_stock: Mapped[int] = mapped_column(Integer, default=0)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0)
    quarantine_quantity: Mapped[int] = mapped_column(Integer, default=0)
    warehouse_location: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Quotation(Base, TimestampMixin):
    __tablename__ = "quotations"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    payment_terms: Mapped[str | None] = mapped_column(String(300))
    warranty_terms: Mapped[str | None] = mapped_column(String(300))
    delivery_terms: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    valid_until: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(10), default="VND")
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    margin_percent: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    customer: Mapped[Customer] = relationship()
    opportunity: Mapped[Opportunity] = relationship()
    items: Mapped[list["QuotationItem"]] = relationship(back_populates="quotation", cascade="all, delete-orphan")


class QuotationItem(Base):
    __tablename__ = "quotation_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    name: Mapped[str] = mapped_column(String(250))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    unit: Mapped[str] = mapped_column(String(30), default="Cái")
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    quotation: Mapped[Quotation] = relationship(back_populates="items")
    product: Mapped["Product | None"] = relationship()


class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"))
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    warranty_terms: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)
    signed_by: Mapped[str | None] = mapped_column(String(160))
    sign_date: Mapped[date | None] = mapped_column(Date)
    effective_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    delivery_scope: Mapped[str | None] = mapped_column(Text)
    customer_signer: Mapped[str | None] = mapped_column(String(160))
    company_signer: Mapped[str | None] = mapped_column(String(160))
    signed_file: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    # informational only; SalesOrder.contract_id (real FK) is the source of truth — see the
    # note on Opportunity.lead_id above for why this side is left unconstrained.
    sales_order_id: Mapped[int | None] = mapped_column(Integer)
    customer: Mapped[Customer] = relationship()
    quotation: Mapped[Quotation | None] = relationship()
    payment_schedule: Mapped[list["ContractPaymentSchedule"]] = relationship(back_populates="contract", cascade="all, delete-orphan")


class ContractPaymentSchedule(Base):
    __tablename__ = "contract_payment_schedules"
    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), index=True)
    description: Mapped[str] = mapped_column(String(250))
    due_condition: Mapped[str | None] = mapped_column(String(250))
    due_date: Mapped[date | None] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    invoiced: Mapped[bool] = mapped_column(Boolean, default=False)
    contract: Mapped[Contract] = relationship(back_populates="payment_schedule")


class StockMovement(Base, TimestampMixin):
    __tablename__ = "stock_movements"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    movement_type: Mapped[str] = mapped_column(String(30))
    quantity: Mapped[int] = mapped_column(Integer)
    reference: Mapped[str | None] = mapped_column(String(100))
    note: Mapped[str | None] = mapped_column(String(300))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    product: Mapped[Product] = relationship()


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(220))
    tax_code: Mapped[str | None] = mapped_column(String(30))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(190))
    address: Mapped[str | None] = mapped_column(String(400))
    contact_person: Mapped[str | None] = mapped_column(String(160))


class PurchaseRequest(Base, TimestampMixin):
    __tablename__ = "purchase_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    department: Mapped[str] = mapped_column(String(100), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    reason: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    product: Mapped[Product] = relationship()
    project: Mapped[Project | None] = relationship()


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    purchase_request_id: Mapped[int | None] = mapped_column(ForeignKey("purchase_requests.id"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    expected_delivery_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    supplier: Mapped[Supplier] = relationship()
    items: Mapped[list["PurchaseOrderItem"]] = relationship(back_populates="purchase_order", cascade="all, delete-orphan")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


class StockReservation(Base, TimestampMixin):
    __tablename__ = "stock_reservations"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    sales_order_id: Mapped[int | None] = mapped_column(ForeignKey("sales_orders.id"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="RESERVED", index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    product: Mapped[Product] = relationship()


class Receivable(Base, TimestampMixin):
    __tablename__ = "receivables"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("sales_orders.id"))
    invoice_no: Mapped[str] = mapped_column(String(60), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), default="OPEN", index=True)
    customer: Mapped[Customer] = relationship()


class SupportTicket(Base, TimestampMixin):
    __tablename__ = "support_tickets"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    sales_order_id: Mapped[int | None] = mapped_column(ForeignKey("sales_orders.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    subject: Mapped[str] = mapped_column(String(250))
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(30), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(50), default="OPEN", index=True)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[str | None] = mapped_column(Text)
    warranty_status: Mapped[str | None] = mapped_column(String(30))
    customer: Mapped[Customer] = relationship()


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(250))
    description: Mapped[str | None] = mapped_column(Text)
    department: Mapped[str] = mapped_column(String(100), index=True)
    assigned_to: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    assigned_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="NEW", index=True)
    progress_note: Mapped[str | None] = mapped_column(Text)
    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assignee: Mapped[User] = relationship(foreign_keys=[assigned_to])
    assigner: Mapped[User] = relationship(foreign_keys=[assigned_by])


class IntegrationLog(Base):
    __tablename__ = "integration_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    system: Mapped[str] = mapped_column(String(30), index=True)
    direction: Mapped[str] = mapped_column(String(20))
    entity: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), index=True)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ApprovalRequest(Base, TimestampMixin):
    __tablename__ = "approval_requests"
    __table_args__ = (Index("ix_approval_requests_entity", "entity_type", "entity_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    reason: Mapped[str | None] = mapped_column(String(300))
    decision_note: Mapped[str | None] = mapped_column(String(300))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requester: Mapped[User | None] = relationship(foreign_keys=[requested_by])
    approver: Mapped[User | None] = relationship(foreign_keys=[approver_id])


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(80))
    details: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(String(64))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    old_values: Mapped[str | None] = mapped_column(Text)
    new_values: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


@event.listens_for(AuditLog, "before_update")
@event.listens_for(AuditLog, "before_delete")
def _immutable_audit_log(*_):
    raise ValueError("Audit log là dữ liệu append-only, không được sửa hoặc xóa")


# VNPRO order-centric orchestration.  SalesOrder is the business spine linking
# CRM, solution engineering, inventory, field execution and finance.
class TechnicalSurvey(Base, TimestampMixin):
    __tablename__ = "technical_surveys"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"), index=True)
    location: Mapped[str | None] = mapped_column(String(300))
    requirements: Mapped[str] = mapped_column(Text)
    current_state: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)
    survey_date: Mapped[date | None] = mapped_column(Date)
    engineer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))


class SolutionBOM(Base, TimestampMixin):
    __tablename__ = "solution_boms"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"), index=True)
    survey_id: Mapped[int | None] = mapped_column(ForeignKey("technical_surveys.id"))
    name: Mapped[str] = mapped_column(String(250))
    scope: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    items: Mapped[list["SolutionBOMItem"]] = relationship(back_populates="bom", cascade="all, delete-orphan")


class SolutionBOMItem(Base):
    __tablename__ = "solution_bom_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    bom_id: Mapped[int] = mapped_column(ForeignKey("solution_boms.id"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    name: Mapped[str] = mapped_column(String(250))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit: Mapped[str] = mapped_column(String(30), default="Cái")
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    note: Mapped[str | None] = mapped_column(Text)
    bom: Mapped[SolutionBOM] = relationship(back_populates="items")


class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), index=True)
    name: Mapped[str] = mapped_column(String(250))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    fulfilled_quantity: Mapped[int] = mapped_column(Integer, default=0)


class SalesInvoice(Base, TimestampMixin):
    __tablename__ = "sales_invoices"
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_no: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    invoice_date: Mapped[date] = mapped_column(Date, default=date.today)
    due_date: Mapped[date] = mapped_column(Date)
    amount_before_vat: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    status: Mapped[str] = mapped_column(String(30), default="ISSUED", index=True)
    issued_by: Mapped[int] = mapped_column(ForeignKey("users.id"))


class PaymentReceipt(Base, TimestampMixin):
    __tablename__ = "payment_receipts"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    receivable_id: Mapped[int] = mapped_column(ForeignKey("receivables.id"), index=True)
    sales_order_id: Mapped[int | None] = mapped_column(ForeignKey("sales_orders.id"), index=True)
    received_date: Mapped[date] = mapped_column(Date, default=date.today)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    method: Mapped[str] = mapped_column(String(30), default="BANK_TRANSFER")
    transaction_ref: Mapped[str | None] = mapped_column(String(100))
    note: Mapped[str | None] = mapped_column(Text)
    received_by: Mapped[int] = mapped_column(ForeignKey("users.id"))


class OrderEvent(Base):
    __tablename__ = "order_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(200))
    details: Mapped[str | None] = mapped_column(Text)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExpensePayment(Base, TimestampMixin):
    __tablename__ = "expense_payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id"), index=True)
    paid_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    method: Mapped[str] = mapped_column(String(30), default="BANK_TRANSFER")
    transaction_ref: Mapped[str | None] = mapped_column(String(100))
    paid_by: Mapped[int] = mapped_column(ForeignKey("users.id"))


class TechnicalRequest(Base, TimestampMixin):
    __tablename__ = "technical_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), index=True)
    sales_order_id: Mapped[int | None] = mapped_column(ForeignKey("sales_orders.id"), index=True)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("support_tickets.id"), index=True)
    request_type: Mapped[str] = mapped_column(String(30))
    scope: Mapped[str] = mapped_column(Text)
    site_address: Mapped[str | None] = mapped_column(String(500))
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    sla_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="NEW", index=True)
    result_note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))


class ApprovalRule(Base, TimestampMixin):
    __tablename__ = "approval_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_type: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(160))
    min_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    max_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    max_discount_percent: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    min_margin_percent: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    over_budget: Mapped[bool | None] = mapped_column(Boolean)
    approver_role: Mapped[str] = mapped_column(String(50))
    step_no: Mapped[int] = mapped_column(Integer, default=1)
    sla_hours: Mapped[int] = mapped_column(Integer, default=24)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class EntityAttachment(Base, TimestampMixin):
    __tablename__ = "entity_attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    document_type: Mapped[str] = mapped_column(String(50))
    file_name: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str | None] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)


class GoodsReceipt(Base, TimestampMixin):
    __tablename__ = "goods_receipts"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id"), index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    received_date: Mapped[date] = mapped_column(Date)
    delivery_note: Mapped[str | None] = mapped_column(String(100))
    document_checklist: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    posted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    lines: Mapped[list["GoodsReceiptLine"]] = relationship(back_populates="receipt", cascade="all, delete-orphan")


class GoodsReceiptLine(Base):
    __tablename__ = "goods_receipt_lines"
    id: Mapped[int] = mapped_column(primary_key=True)
    goods_receipt_id: Mapped[int] = mapped_column(ForeignKey("goods_receipts.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    received_quantity: Mapped[int] = mapped_column(Integer)
    accepted_quantity: Mapped[int] = mapped_column(Integer, default=0)
    quarantine_quantity: Mapped[int] = mapped_column(Integer, default=0)
    rejected_quantity: Mapped[int] = mapped_column(Integer, default=0)
    quality_note: Mapped[str | None] = mapped_column(Text)
    receipt: Mapped[GoodsReceipt] = relationship(back_populates="lines")


class CollectionActivity(Base, TimestampMixin):
    __tablename__ = "collection_activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    receivable_id: Mapped[int] = mapped_column(ForeignKey("receivables.id"), index=True)
    activity_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    channel: Mapped[str] = mapped_column(String(30))
    result: Mapped[str] = mapped_column(Text)
    promised_date: Mapped[date | None] = mapped_column(Date)
    promised_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    next_follow_up: Mapped[date | None] = mapped_column(Date)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))


class WarrantyProfile(Base, TimestampMixin):
    __tablename__ = "warranty_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    serial_no: Mapped[str | None] = mapped_column(String(100), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    coverage: Mapped[str] = mapped_column(Text)
    exclusions: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)


class TicketEvent(Base, TimestampMixin):
    __tablename__ = "ticket_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("support_tickets.id"), index=True)
    action: Mapped[str] = mapped_column(String(40))
    note: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
