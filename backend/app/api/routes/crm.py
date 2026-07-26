from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from app.api.deps import require_permission
from app.approvals import decide_approval, request_approval, resolve_rule_role, resolve_user_by_role
from app.core.permissions import Permission
from app.core.workflow import assert_transition, quotation_needs_director_approval, DECISION_TARGETS
from app.db.session import get_db
from app.models import ApprovalRequest, Contract, ContractPaymentSchedule, Customer, Lead, Opportunity, Quotation, QuotationItem, SalesOrder, SalesOrderItem, User
from app.schemas import (
    ContractCreate, ContractGenerateOrder, ContractOut, ContractSign, DecisionNote,
    LeadConvert, LeadCreate, LeadOut, LeadStatusUpdate,
    OrderOut, QuotationCreate, QuotationOut,
)
from app.services import audit

router = APIRouter(prefix="/crm", tags=["CRM"])


def _pending_approval(db: Session, entity_type: str, entity_id: int) -> ApprovalRequest | None:
    return db.scalar(select(ApprovalRequest).where(ApprovalRequest.entity_type == entity_type, ApprovalRequest.entity_id == entity_id, ApprovalRequest.status == "PENDING"))


def _authorize_decision(approval: ApprovalRequest, user: User) -> None:
    if approval.approver_id and approval.approver_id != user.id and user.role not in {"DIRECTOR", "SYSTEM_ADMIN"}:
        raise HTTPException(403, "Bạn không phải người được giao phê duyệt yêu cầu này")


def _decide(db: Session, entity_type: str, entity, user: User, approve: bool, note: str | None):
    approval = _pending_approval(db, entity_type, entity.id)
    if not approval:
        raise HTTPException(404, "Không có yêu cầu phê duyệt đang chờ xử lý")
    _authorize_decision(approval, user)
    targets = DECISION_TARGETS[entity_type]
    try:
        decide_approval(db, approval=approval, entity=entity, decided_by=user, approve=approve, note=note, approved_status=targets["approved"], rejected_status=targets["rejected"])
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    db.commit(); db.refresh(entity)


def _quotation_total(items) -> Decimal:
    return sum((Decimal(i.quantity) * i.unit_price * (Decimal(1) - i.discount_percent / Decimal(100)) * (Decimal(1) + i.tax_rate / Decimal(100)) for i in items), Decimal(0))


def _quotation_cost(items) -> Decimal:
    return sum((Decimal(i.quantity) * i.estimated_cost for i in items), Decimal(0))


def _quotation_net(items) -> Decimal:
    return sum((Decimal(i.quantity) * i.unit_price * (Decimal(1) - i.discount_percent / Decimal(100)) for i in items), Decimal(0))


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------

@router.get("/leads", response_model=list[LeadOut])
def leads(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.SALES_READ))):
    return db.scalars(select(Lead).order_by(Lead.created_at.desc())).all()


@router.post("/leads", response_model=LeadOut, status_code=201)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    if db.scalar(select(Lead).where(Lead.code == payload.code)):
        raise HTTPException(409, "Mã lead đã tồn tại")
    item = Lead(**payload.model_dump(), owner_id=user.id, status="NEW")
    db.add(item); db.flush(); audit(db, user, "CREATE", "LEAD", item.id, item.company_name); db.commit(); db.refresh(item)
    return item


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.SALES_READ))):
    item = db.get(Lead, lead_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy lead")
    return item


@router.patch("/leads/{lead_id}/status", response_model=LeadOut)
def update_lead_status(lead_id: int, payload: LeadStatusUpdate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    item = db.get(Lead, lead_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy lead")
    assert_transition("LEAD", item.status, payload.status)
    item.status = payload.status
    audit(db, user, "UPDATE_STATUS", "LEAD", item.id, payload.status)
    db.commit(); db.refresh(item)
    return item


@router.post("/leads/{lead_id}/convert", response_model=LeadOut)
def convert_lead(lead_id: int, payload: LeadConvert, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Không tìm thấy lead")
    assert_transition("LEAD", lead.status, "CONVERTED")
    if payload.customer_id:
        customer = db.get(Customer, payload.customer_id)
        if not customer:
            raise HTTPException(404, "Không tìm thấy khách hàng")
    else:
        code = f"KH-{lead.code}"
        if db.scalar(select(Customer).where(Customer.code == code)):
            raise HTTPException(409, "Không thể tự tạo khách hàng: mã đã tồn tại, hãy chọn customer_id có sẵn")
        customer = Customer(code=code, name=lead.company_name, phone=lead.phone, email=lead.email, owner_id=user.id)
        db.add(customer); db.flush()
    opportunity = Opportunity(
        code=payload.opportunity_code, customer_id=customer.id, title=payload.opportunity_title, stage="QUALIFICATION",
        expected_value=payload.expected_value, probability=payload.probability, expected_close_date=payload.expected_close_date,
        owner_id=user.id, lead_id=lead.id,
    )
    db.add(opportunity); db.flush()
    lead.status = "CONVERTED"
    lead.converted_to_opportunity_id = opportunity.id
    audit(db, user, "CONVERT", "LEAD", lead.id, f"-> OPPORTUNITY {opportunity.code}")
    db.commit(); db.refresh(lead)
    return lead


# ---------------------------------------------------------------------------
# Quotations
# ---------------------------------------------------------------------------

@router.get("/quotations", response_model=list[QuotationOut])
def quotations(opportunity_id: int | None = Query(default=None), db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.SALES_READ))):
    stmt = select(Quotation).options(selectinload(Quotation.items)).order_by(Quotation.created_at.desc())
    if opportunity_id:
        stmt = stmt.where(Quotation.opportunity_id == opportunity_id)
    return db.scalars(stmt).all()


@router.post("/quotations", response_model=QuotationOut, status_code=201)
def create_quotation(payload: QuotationCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    if db.scalar(select(Quotation).where(Quotation.code == payload.code)):
        raise HTTPException(409, "Mã báo giá đã tồn tại")
    opportunity = db.get(Opportunity, payload.opportunity_id)
    if not opportunity:
        raise HTTPException(404, "Không tìm thấy cơ hội")
    if opportunity.customer_id != payload.customer_id:
        raise HTTPException(422, "Khách hàng báo giá không trùng khách hàng của cơ hội")
    data = payload.model_dump(exclude={"items"})
    item = Quotation(**data, status="DRAFT", created_by=user.id, total_amount=0)
    item.items = [QuotationItem(**i.model_dump()) for i in payload.items]
    item.total_amount = _quotation_total(item.items)
    item.estimated_cost = _quotation_cost(item.items)
    net_revenue = _quotation_net(item.items)
    item.margin_percent = ((net_revenue - item.estimated_cost) / net_revenue * 100) if net_revenue else 0
    db.add(item); db.flush(); audit(db, user, "CREATE", "QUOTATION", item.id, item.code); db.commit(); db.refresh(item)
    return item


@router.post("/quotations/{quotation_id}/clone", response_model=QuotationOut, status_code=201)
def clone_quotation(quotation_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    source = db.scalar(select(Quotation).options(selectinload(Quotation.items)).where(Quotation.id == quotation_id))
    if not source:
        raise HTTPException(404, "Không tìm thấy báo giá")
    base = source.code.rsplit("-V", 1)[0]
    version = (db.scalar(select(func.max(Quotation.version_no)).where(Quotation.opportunity_id == source.opportunity_id)) or source.version_no) + 1
    code = f"{base}-V{version}"
    if db.scalar(select(Quotation).where(Quotation.code == code)):
        raise HTTPException(409, "Mã version báo giá đã tồn tại")
    row = Quotation(code=code, opportunity_id=source.opportunity_id, customer_id=source.customer_id,
                    total_amount=source.total_amount, payment_terms=source.payment_terms,
                    warranty_terms=source.warranty_terms, delivery_terms=source.delivery_terms,
                    valid_until=source.valid_until, currency=source.currency, estimated_cost=source.estimated_cost,
                    margin_percent=source.margin_percent, version_no=version, status="DRAFT", created_by=user.id)
    row.items = [QuotationItem(product_id=x.product_id, name=x.name, quantity=x.quantity, unit_price=x.unit_price,
                               discount_percent=x.discount_percent, unit=x.unit, tax_rate=x.tax_rate,
                               estimated_cost=x.estimated_cost) for x in source.items]
    db.add(row); db.flush(); audit(db, user, "CREATE_VERSION", "QUOTATION", row.id, f"From {source.code}"); db.commit()
    return row


@router.get("/quotations/{quotation_id}", response_model=QuotationOut)
def get_quotation(quotation_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.SALES_READ))):
    item = db.scalar(select(Quotation).options(selectinload(Quotation.items)).where(Quotation.id == quotation_id))
    if not item:
        raise HTTPException(404, "Không tìm thấy báo giá")
    return item


@router.post("/quotations/{quotation_id}/submit", response_model=QuotationOut)
def submit_quotation(quotation_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    item = db.scalar(select(Quotation).options(selectinload(Quotation.items)).where(Quotation.id == quotation_id))
    if not item:
        raise HTTPException(404, "Không tìm thấy báo giá")
    assert_transition("QUOTATION", item.status, "SUBMITTED")
    max_discount = max((i.discount_percent for i in item.items), default=Decimal(0))
    needs_director = quotation_needs_director_approval(item.total_amount, max_discount)
    approver_role = resolve_rule_role(
        db, "QUOTATION", amount=item.total_amount, discount=max_discount, margin=item.margin_percent
    ) or ("DIRECTOR" if needs_director else "SALES_ADMIN")
    approver = resolve_user_by_role(db, approver_role)
    reason = "Vượt hạn mức chiết khấu/giá trị báo giá" if needs_director else None
    request_approval(db, entity_type="QUOTATION", entity=item, requested_by=user, approver_id=approver.id if approver else None, reason=reason, pending_status="SUBMITTED")
    db.commit(); db.refresh(item)
    return item


@router.post("/quotations/{quotation_id}/approve", response_model=QuotationOut)
def approve_quotation(quotation_id: int, payload: DecisionNote, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_APPROVE))):
    item = db.get(Quotation, quotation_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy báo giá")
    _decide(db, "QUOTATION", item, user, True, payload.note)
    item.locked_at = datetime.now(timezone.utc); db.commit(); db.refresh(item)
    return item


@router.post("/quotations/{quotation_id}/reject", response_model=QuotationOut)
def reject_quotation(quotation_id: int, payload: DecisionNote, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_APPROVE))):
    item = db.get(Quotation, quotation_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy báo giá")
    _decide(db, "QUOTATION", item, user, False, payload.note)
    return item


@router.post("/quotations/{quotation_id}/send", response_model=QuotationOut)
def send_quotation(quotation_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    item = db.get(Quotation, quotation_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy báo giá")
    assert_transition("QUOTATION", item.status, "SENT_TO_CUSTOMER")
    item.status = "SENT_TO_CUSTOMER"
    opportunity = db.get(Opportunity, item.opportunity_id)
    if opportunity and opportunity.stage in {"LEAD", "QUALIFICATION", "TECHNICAL_SURVEY"}:
        opportunity.stage = "PROPOSAL"
    audit(db, user, "SEND", "QUOTATION", item.id, item.code)
    db.commit(); db.refresh(item)
    return item


@router.post("/quotations/{quotation_id}/convert-to-contract", response_model=ContractOut, status_code=201)
def convert_quotation_to_contract(quotation_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(404, "Không tìm thấy báo giá")
    assert_transition("QUOTATION", quotation.status, "WON")
    code = f"HD-{quotation.code}"
    if db.scalar(select(Contract).where(Contract.code == code)):
        raise HTTPException(409, "Mã hợp đồng tự sinh đã tồn tại")
    contract = Contract(
        code=code, quotation_id=quotation.id, customer_id=quotation.customer_id, opportunity_id=quotation.opportunity_id,
        total_value=quotation.total_amount, warranty_terms=quotation.warranty_terms, status="DRAFT", created_by=user.id,
    )
    contract.payment_schedule = [ContractPaymentSchedule(description="Thanh toán theo hợp đồng", amount=quotation.total_amount)]
    db.add(contract); db.flush()
    quotation.status = "WON"
    opportunity = db.get(Opportunity, quotation.opportunity_id)
    if opportunity:
        opportunity.stage = "NEGOTIATION"
    audit(db, user, "CONVERT", "QUOTATION", quotation.id, f"-> CONTRACT {contract.code}")
    db.commit(); db.refresh(contract)
    return contract


# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------

@router.get("/contracts", response_model=list[ContractOut])
def contracts(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.SALES_READ))):
    return db.scalars(select(Contract).options(selectinload(Contract.payment_schedule)).order_by(Contract.created_at.desc())).all()


@router.post("/contracts", response_model=ContractOut, status_code=201)
def create_contract(payload: ContractCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    if db.scalar(select(Contract).where(Contract.code == payload.code)):
        raise HTTPException(409, "Mã hợp đồng đã tồn tại")
    if payload.quotation_id:
        quotation = db.get(Quotation, payload.quotation_id)
        if not quotation or quotation.status not in ["APPROVED", "SENT_TO_CUSTOMER", "WON"]:
            raise HTTPException(422, "Hợp đồng chỉ được tham chiếu báo giá đã duyệt")
        if quotation.customer_id != payload.customer_id or (
            payload.opportunity_id is not None and quotation.opportunity_id != payload.opportunity_id
        ):
            raise HTTPException(422, "Hợp đồng không cùng khách hàng/cơ hội với báo giá")
        if payload.total_value != quotation.total_amount:
            raise HTTPException(422, "Giá trị hợp đồng phải khớp báo giá đã duyệt")
    if not payload.payment_schedule or sum((x.amount for x in payload.payment_schedule), Decimal(0)) != payload.total_value:
        raise HTTPException(422, "Tổng lịch thanh toán phải bằng giá trị hợp đồng")
    if payload.expiry_date and payload.effective_date and payload.expiry_date < payload.effective_date:
        raise HTTPException(422, "Ngày hết hạn phải sau ngày hiệu lực")
    data = payload.model_dump(exclude={"payment_schedule"})
    item = Contract(**data, status="DRAFT", created_by=user.id)
    item.payment_schedule = [ContractPaymentSchedule(**p.model_dump()) for p in payload.payment_schedule]
    db.add(item); db.flush(); audit(db, user, "CREATE", "CONTRACT", item.id, item.code); db.commit(); db.refresh(item)
    return item


@router.get("/contracts/{contract_id}", response_model=ContractOut)
def get_contract(contract_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.SALES_READ))):
    item = db.scalar(select(Contract).options(selectinload(Contract.payment_schedule)).where(Contract.id == contract_id))
    if not item:
        raise HTTPException(404, "Không tìm thấy hợp đồng")
    return item


@router.post("/contracts/{contract_id}/submit", response_model=ContractOut)
def submit_contract(contract_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    item = db.get(Contract, contract_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy hợp đồng")
    assert_transition("CONTRACT", item.status, "INTERNAL_REVIEW")
    director = resolve_user_by_role(db, "DIRECTOR")
    request_approval(db, entity_type="CONTRACT", entity=item, requested_by=user, approver_id=director.id if director else None, reason=None, pending_status="INTERNAL_REVIEW")
    db.commit(); db.refresh(item)
    return item


@router.post("/contracts/{contract_id}/approve", response_model=ContractOut)
def approve_contract(contract_id: int, payload: DecisionNote, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_APPROVE))):
    item = db.get(Contract, contract_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy hợp đồng")
    _decide(db, "CONTRACT", item, user, True, payload.note)
    return item


@router.post("/contracts/{contract_id}/reject", response_model=ContractOut)
def reject_contract(contract_id: int, payload: DecisionNote, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_APPROVE))):
    item = db.get(Contract, contract_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy hợp đồng")
    _decide(db, "CONTRACT", item, user, False, payload.note)
    return item


@router.post("/contracts/{contract_id}/send-for-signature", response_model=ContractOut)
def send_contract_for_signature(contract_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    item = db.get(Contract, contract_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy hợp đồng")
    assert_transition("CONTRACT", item.status, "SENT_FOR_SIGNATURE")
    item.status = "SENT_FOR_SIGNATURE"
    audit(db, user, "SEND_FOR_SIGNATURE", "CONTRACT", item.id, item.code)
    db.commit(); db.refresh(item)
    return item


@router.post("/contracts/{contract_id}/sign", response_model=ContractOut)
def sign_contract(contract_id: int, payload: ContractSign, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    item = db.get(Contract, contract_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy hợp đồng")
    assert_transition("CONTRACT", item.status, "SIGNED")
    item.status = "SIGNED"
    item.signed_by = payload.signed_by
    item.sign_date = payload.sign_date
    item.customer_signer = payload.customer_signer
    item.company_signer = payload.company_signer
    item.signed_file = payload.signed_file
    audit(db, user, "SIGN", "CONTRACT", item.id, payload.signed_by)
    db.commit(); db.refresh(item)
    return item


@router.post("/contracts/{contract_id}/generate-sales-order", response_model=OrderOut, status_code=201)
def generate_sales_order(contract_id: int, payload: ContractGenerateOrder, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(404, "Không tìm thấy hợp đồng")
    assert_transition("CONTRACT", contract.status, "ACTIVE")
    if not contract.sign_date or not contract.customer_signer or not contract.company_signer or not contract.signed_file:
        raise HTTPException(422, "Hợp đồng phải có đầy đủ hồ sơ ký trước khi sinh đơn hàng")
    if contract.expiry_date and contract.expiry_date < datetime.now(timezone.utc).date():
        raise HTTPException(409, "Hợp đồng đã hết hiệu lực")
    if db.scalar(select(SalesOrder).where(SalesOrder.code == payload.code)):
        raise HTTPException(409, "Mã đơn hàng đã tồn tại")
    order = SalesOrder(
        code=payload.code, customer_id=contract.customer_id, opportunity_id=contract.opportunity_id, contract_id=contract.id,
        title=payload.title or f"Theo hợp đồng {contract.code}", status="DRAFT", total_amount=contract.total_value, created_by=user.id,
    )
    db.add(order); db.flush()
    if contract.quotation_id:
        quotation = db.scalar(select(Quotation).options(selectinload(Quotation.items)).where(Quotation.id == contract.quotation_id))
        order.cost_estimate = quotation.estimated_cost
        for line in quotation.items:
            effective_unit_price = line.unit_price * (Decimal(1) - line.discount_percent / Decimal(100)) * (Decimal(1) + line.tax_rate / Decimal(100))
            db.add(SalesOrderItem(sales_order_id=order.id, product_id=line.product_id, name=line.name,
                                  quantity=line.quantity, unit_price=effective_unit_price))
    contract.status = "ACTIVE"
    contract.sales_order_id = order.id
    if contract.opportunity_id:
        opportunity = db.get(Opportunity, contract.opportunity_id)
        if opportunity:
            opportunity.stage = "WON"
    audit(db, user, "GENERATE_ORDER", "CONTRACT", contract.id, order.code)
    db.commit(); db.refresh(order)
    return order
