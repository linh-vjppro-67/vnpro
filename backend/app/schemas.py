from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    department: str
    is_active: bool


class CustomerCreate(BaseModel):
    code: str
    name: str
    tax_code: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    segment: str = "Doanh nghiệp"


class CustomerOut(CustomerCreate, ORMModel):
    id: int
    owner_id: int | None = None
    created_at: datetime


class OpportunityCreate(BaseModel):
    code: str
    customer_id: int
    title: str
    stage: str = "LEAD"
    expected_value: Decimal = 0
    probability: int = Field(default=10, ge=0, le=100)
    expected_close_date: date | None = None
    lead_id: int | None = None


class OpportunityOut(OpportunityCreate, ORMModel):
    id: int
    owner_id: int | None = None
    created_at: datetime


class OrderCreate(BaseModel):
    code: str
    customer_id: int
    opportunity_id: int | None = None
    contract_id: int | None = None
    title: str
    status: str = "DRAFT"
    total_amount: Decimal = 0
    cost_estimate: Decimal = 0
    payment_status: str = "UNPAID"
    due_date: date | None = None


class OrderOut(OrderCreate, ORMModel):
    id: int
    created_by: int | None = None
    created_at: datetime


class LeadCreate(BaseModel):
    code: str
    source: str = "OTHER"
    company_name: str
    contact_name: str
    phone: str | None = None
    email: EmailStr | None = None
    need_summary: str | None = None
    potential_level: str = "MEDIUM"


class LeadOut(LeadCreate, ORMModel):
    id: int
    owner_id: int | None = None
    status: str
    converted_to_opportunity_id: int | None = None
    created_at: datetime


class LeadStatusUpdate(BaseModel):
    status: str


class LeadConvert(BaseModel):
    customer_id: int | None = None
    opportunity_code: str
    opportunity_title: str
    expected_value: Decimal = 0
    probability: int = Field(default=20, ge=0, le=100)
    expected_close_date: date | None = None


class QuotationItemCreate(BaseModel):
    product_id: int | None = None
    name: str
    quantity: int = Field(default=1, gt=0)
    unit_price: Decimal = Field(ge=0)
    discount_percent: Decimal = Field(default=0, ge=0, le=100)


class QuotationItemOut(QuotationItemCreate, ORMModel):
    id: int


class QuotationCreate(BaseModel):
    code: str
    opportunity_id: int
    customer_id: int
    payment_terms: str | None = None
    warranty_terms: str | None = None
    delivery_terms: str | None = None
    items: list[QuotationItemCreate] = Field(default_factory=list)


class QuotationOut(ORMModel):
    id: int
    code: str
    opportunity_id: int
    customer_id: int
    total_amount: Decimal
    payment_terms: str | None
    warranty_terms: str | None
    delivery_terms: str | None
    status: str
    created_by: int | None
    approved_by: int | None
    created_at: datetime
    items: list[QuotationItemOut] = []


class ContractPaymentScheduleCreate(BaseModel):
    description: str
    due_condition: str | None = None
    due_date: date | None = None
    amount: Decimal = Field(ge=0)
    invoiced: bool = False


class ContractPaymentScheduleOut(ContractPaymentScheduleCreate, ORMModel):
    id: int


class ContractCreate(BaseModel):
    code: str
    quotation_id: int | None = None
    customer_id: int
    opportunity_id: int | None = None
    total_value: Decimal = 0
    warranty_terms: str | None = None
    payment_schedule: list[ContractPaymentScheduleCreate] = Field(default_factory=list)


class ContractOut(ORMModel):
    id: int
    code: str
    quotation_id: int | None
    customer_id: int
    opportunity_id: int | None
    total_value: Decimal
    warranty_terms: str | None
    status: str
    signed_by: str | None
    created_by: int | None
    approved_by: int | None
    sales_order_id: int | None
    created_at: datetime
    payment_schedule: list[ContractPaymentScheduleOut] = []


class ContractSign(BaseModel):
    signed_by: str


class ContractGenerateOrder(BaseModel):
    code: str
    title: str | None = None


class DecisionNote(BaseModel):
    note: str | None = None


class ApprovalDecision(BaseModel):
    approve: bool
    note: str | None = None


class ApprovalRequestOut(ORMModel):
    id: int
    entity_type: str
    entity_id: int
    requested_by: int | None
    approver_id: int | None
    status: str
    reason: str | None
    decision_note: str | None
    decided_at: datetime | None
    created_at: datetime


class OrderUpdate(BaseModel):
    status: str | None = None
    payment_status: str | None = None
    total_amount: Decimal | None = None
    cost_estimate: Decimal | None = None
    due_date: date | None = None


class ProjectCreate(BaseModel):
    code: str
    name: str
    order_id: int
    manager_id: int | None = None
    start_date: date | None = None
    due_date: date | None = None
    budget_amount: Decimal = 0


class ProjectOut(ORMModel):
    id: int
    code: str
    name: str
    customer_id: int
    order_id: int | None
    status: str
    manager_id: int | None
    start_date: date | None
    due_date: date | None
    progress: int
    budget_amount: Decimal
    actual_cost: Decimal


class WorkOrderCreate(BaseModel):
    code: str
    project_id: int
    title: str
    location: str | None = None
    scheduled_date: date | None = None
    technician_id: int | None = None
    materials_needed: str | None = None
    checklist: str | None = None


class WorkOrderOut(WorkOrderCreate, ORMModel):
    id: int
    status: str
    created_by: int | None = None
    created_at: datetime


class AcceptanceRecordCreate(BaseModel):
    code: str
    work_order_id: int
    summary: str | None = None
    customer_signed_by: str | None = None


class AcceptanceRecordOut(ORMModel):
    id: int
    code: str
    work_order_id: int
    project_id: int
    summary: str | None
    customer_signed_by: str | None
    status: str
    created_by: int | None
    approved_by: int | None
    created_at: datetime


class BudgetOut(ORMModel):
    id: int
    code: str
    name: str
    department: str
    period: str
    amount: Decimal
    spent_amount: Decimal
    status: str


class ExpenseCreate(BaseModel):
    code: str
    description: str
    amount: Decimal = Field(gt=0)
    category: str
    department: str
    project_id: int | None = None
    expense_date: date = Field(default_factory=date.today)


class ExpenseOut(ExpenseCreate, ORMModel):
    id: int
    status: str
    created_by: int | None = None
    approved_by: int | None = None
    created_at: datetime


class SupplierCreate(BaseModel):
    code: str
    name: str
    tax_code: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    contact_person: str | None = None


class SupplierOut(SupplierCreate, ORMModel):
    id: int
    created_at: datetime


class PurchaseRequestCreate(BaseModel):
    code: str
    department: str
    project_id: int | None = None
    product_id: int
    quantity: int = Field(gt=0)
    reason: str | None = None


class PurchaseRequestOut(PurchaseRequestCreate, ORMModel):
    id: int
    status: str
    created_by: int | None = None
    approved_by: int | None = None
    created_at: datetime


class PurchaseOrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class PurchaseOrderItemOut(PurchaseOrderItemCreate, ORMModel):
    id: int


class PurchaseOrderCreate(BaseModel):
    code: str
    supplier_id: int
    purchase_request_id: int | None = None
    expected_delivery_date: date | None = None
    items: list[PurchaseOrderItemCreate] = Field(default_factory=list)


class PurchaseOrderOut(ORMModel):
    id: int
    code: str
    supplier_id: int
    purchase_request_id: int | None
    total_amount: Decimal
    expected_delivery_date: date | None
    status: str
    created_by: int | None
    created_at: datetime
    items: list[PurchaseOrderItemOut] = []


class StockReservationCreate(BaseModel):
    product_id: int
    sales_order_id: int | None = None
    project_id: int | None = None
    quantity: int = Field(gt=0)


class StockReservationOut(StockReservationCreate, ORMModel):
    id: int
    status: str
    created_by: int | None = None
    created_at: datetime


class ProductOut(ORMModel):
    id: int
    sku: str
    name: str
    category: str
    unit: str
    sale_price: Decimal
    cost_price: Decimal
    min_stock: int
    quantity_on_hand: int
    reserved_quantity: int


class StockMovementCreate(BaseModel):
    product_id: int
    movement_type: str
    quantity: int = Field(gt=0)
    reference: str | None = None
    note: str | None = None


class ReceivableOut(ORMModel):
    id: int
    customer_id: int
    order_id: int | None
    invoice_no: str
    amount: Decimal
    paid_amount: Decimal
    due_date: date
    status: str


class ReceivableCreate(BaseModel):
    order_id: int | None = None
    customer_id: int
    invoice_no: str
    amount: Decimal
    due_date: date


class ReceivablePayment(BaseModel):
    paid_amount: Decimal


class SupportTicketCreate(BaseModel):
    code: str
    customer_id: int
    project_id: int | None = None
    subject: str
    priority: str = "MEDIUM"


class SupportTicketOut(SupportTicketCreate, ORMModel):
    id: int
    status: str
    assigned_to: int | None = None
    sla_due_at: datetime | None = None
    created_at: datetime


class IntegrationLogOut(ORMModel):
    id: int
    system: str
    direction: str
    entity: str
    status: str
    message: str
    created_at: datetime


class AuditLogOut(ORMModel):
    id: int
    user_id: int | None
    action: str
    entity: str
    entity_id: str | None
    details: str | None
    created_at: datetime


class TaskCreate(BaseModel):
    code: str
    title: str
    description: str | None = None
    department: str
    assigned_to: int
    priority: str = "MEDIUM"
    due_date: date | None = None


class TaskOut(TaskCreate, ORMModel):
    id: int
    assigned_by: int
    status: str
    progress_note: str | None = None
    confirmed_by: int | None = None
    confirmed_at: datetime | None = None
    created_at: datetime


class TaskProgressNote(BaseModel):
    note: str | None = None


class DashboardSummary(BaseModel):
    revenue: Decimal
    gross_profit: Decimal
    pipeline_value: Decimal
    open_receivables: Decimal
    overdue_receivables: Decimal
    approved_budget: Decimal
    spent_budget: Decimal
    active_projects: int
    open_tickets: int
    low_stock_products: int
    monthly_revenue: list[dict]
    sales_funnel: list[dict]
    expense_by_category: list[dict]
    alerts: list[dict]


TokenResponse.model_rebuild()
