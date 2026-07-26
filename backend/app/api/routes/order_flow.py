from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.deps import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.domain import receive_payment
from app.models import (
    AcceptanceRecord, Contract, Customer, Opportunity, OrderEvent, PaymentReceipt,
    Product, Project, PurchaseRequest, Receivable, SalesInvoice, SalesOrder,
    SalesOrderItem, SolutionBOM, SolutionBOMItem, StockMovement, StockReservation,
    TechnicalSurvey, User, WorkOrder,
)
from app.services import audit

router = APIRouter(prefix="/order-flow", tags=["VNPRO Order Flow"])


class SurveyIn(BaseModel):
    code: str
    opportunity_id: int
    location: str | None = None
    requirements: str
    current_state: str | None = None
    recommendation: str | None = None
    survey_date: date | None = None
    engineer_id: int | None = None


class BOMLineIn(BaseModel):
    product_id: int | None = None
    name: str
    quantity: int = Field(gt=0)
    unit: str = "Cái"
    estimated_cost: Decimal = Field(default=0, ge=0)
    note: str | None = None


class BOMIn(BaseModel):
    code: str
    opportunity_id: int
    survey_id: int | None = None
    name: str
    scope: str | None = None
    items: list[BOMLineIn] = Field(min_length=1)


class OrderLineIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class ProjectIn(BaseModel):
    code: str
    manager_id: int | None = None
    start_date: date | None = None
    due_date: date | None = None


class InvoiceIn(BaseModel):
    invoice_no: str
    due_date: date
    amount_before_vat: Decimal = Field(gt=0)
    vat_amount: Decimal = Field(default=0, ge=0)


class ReceiptIn(BaseModel):
    code: str
    receivable_id: int
    amount: Decimal = Field(gt=0)
    received_date: date = Field(default_factory=date.today)
    method: str = "BANK_TRANSFER"
    transaction_ref: str | None = None
    note: str | None = None


def row_dict(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def require_row(db, model, row_id, message="Không tìm thấy dữ liệu"):
    row = db.get(model, row_id)
    if not row:
        raise HTTPException(404, message)
    return row


def event(db, order, user, event_type, title, details=None):
    db.add(OrderEvent(sales_order_id=order.id, event_type=event_type, title=title, details=details, actor_id=user.id))
    audit(db, user, event_type, "SALES_ORDER", order.id, details or title)


def inventory_snapshot(db, order_id):
    lines = db.scalars(select(SalesOrderItem).where(SalesOrderItem.sales_order_id == order_id)).all()
    result = []
    enough = bool(lines)
    for line in lines:
        if line.product_id is None:
            result.append({
                **row_dict(line), "sku": "DỊCH VỤ", "stock_on_hand": 0,
                "stock_reserved_total": 0, "reserved_for_order": 0,
                "available": 0, "shortage": 0, "non_inventory": True,
            })
            continue
        product = db.get(Product, line.product_id)
        reserved = db.scalar(select(func.coalesce(func.sum(StockReservation.quantity), 0)).where(
            StockReservation.sales_order_id == order_id,
            StockReservation.product_id == line.product_id,
            StockReservation.status == "RESERVED",
        )) or 0
        available = max(0, product.quantity_on_hand - product.reserved_quantity)
        shortage = max(0, line.quantity - reserved - available)
        enough = enough and shortage == 0
        result.append({
            **row_dict(line), "sku": product.sku, "stock_on_hand": product.quantity_on_hand,
            "stock_reserved_total": product.reserved_quantity, "reserved_for_order": reserved,
            "available": available, "shortage": shortage,
        })
    return result, enough


@router.get("/master-data")
def master_data(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.SALES_READ))):
    return {
        "opportunities": [row_dict(x) for x in db.scalars(select(Opportunity).order_by(Opportunity.created_at.desc())).all()],
        "products": [row_dict(x) for x in db.scalars(select(Product).order_by(Product.name)).all()],
        "users": [{"id": x.id, "full_name": x.full_name, "role": x.role} for x in db.scalars(select(User).where(User.is_active).order_by(User.full_name)).all()],
    }


@router.get("/surveys")
def list_surveys(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.OPERATIONS_READ))):
    return [row_dict(x) for x in db.scalars(select(TechnicalSurvey).order_by(TechnicalSurvey.created_at.desc())).all()]


@router.post("/surveys", status_code=201)
def create_survey(payload: SurveyIn, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.OPERATIONS_WRITE))):
    opportunity = require_row(db, Opportunity, payload.opportunity_id, "Không tìm thấy cơ hội")
    if db.scalar(select(TechnicalSurvey).where(TechnicalSurvey.code == payload.code)):
        raise HTTPException(409, "Mã khảo sát đã tồn tại")
    row = TechnicalSurvey(**payload.model_dump(), status="COMPLETED", created_by=user.id)
    opportunity.stage = "TECHNICAL_SURVEY"
    db.add(row); db.flush(); audit(db, user, "CREATE", "TECHNICAL_SURVEY", row.id, row.code); db.commit()
    return row_dict(row)


@router.get("/boms")
def list_boms(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.OPERATIONS_READ))):
    result = []
    for row in db.scalars(select(SolutionBOM).order_by(SolutionBOM.created_at.desc())).all():
        result.append({**row_dict(row), "items": [row_dict(x) for x in row.items]})
    return result


@router.post("/boms", status_code=201)
def create_bom(payload: BOMIn, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.OPERATIONS_WRITE))):
    opportunity = require_row(db, Opportunity, payload.opportunity_id, "Không tìm thấy cơ hội")
    if payload.survey_id:
        survey = require_row(db, TechnicalSurvey, payload.survey_id, "Không tìm thấy khảo sát")
        if survey.opportunity_id != opportunity.id:
            raise HTTPException(422, "Khảo sát không thuộc cơ hội")
    if db.scalar(select(SolutionBOM).where(SolutionBOM.code == payload.code)):
        raise HTTPException(409, "Mã BOM đã tồn tại")
    row = SolutionBOM(**payload.model_dump(exclude={"items"}), status="APPROVED", created_by=user.id)
    row.items = [SolutionBOMItem(**x.model_dump()) for x in payload.items]
    db.add(row); db.flush(); audit(db, user, "CREATE", "SOLUTION_BOM", row.id, row.code); db.commit()
    return {**row_dict(row), "items": [row_dict(x) for x in row.items]}


@router.get("/orders")
def list_orders(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.SALES_READ))):
    result = []
    for order in db.scalars(select(SalesOrder).order_by(SalesOrder.created_at.desc())).all():
        project = db.scalar(select(Project).where(Project.order_id == order.id))
        receivables = db.scalars(select(Receivable).where(Receivable.order_id == order.id)).all()
        items, enough = inventory_snapshot(db, order.id)
        result.append({
            **row_dict(order), "project_id": project.id if project else None,
            "item_count": len(items), "inventory_ready": enough,
            "invoiced_amount": sum((Decimal(x.amount) for x in receivables), Decimal(0)),
            "received_amount": sum((Decimal(x.paid_amount) for x in receivables), Decimal(0)),
        })
    return result


@router.get("/orders/{order_id}/workspace")
def workspace(order_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.SALES_READ))):
    order = require_row(db, SalesOrder, order_id, "Không tìm thấy đơn hàng")
    customer = db.get(Customer, order.customer_id)
    contract = db.get(Contract, order.contract_id) if order.contract_id else None
    project = db.scalar(select(Project).where(Project.order_id == order.id))
    items, enough = inventory_snapshot(db, order.id)
    work_orders = db.scalars(select(WorkOrder).where(WorkOrder.project_id == project.id).order_by(WorkOrder.created_at) if project else select(WorkOrder).where(False)).all()
    acceptances = db.scalars(select(AcceptanceRecord).where(AcceptanceRecord.project_id == project.id).order_by(AcceptanceRecord.created_at) if project else select(AcceptanceRecord).where(False)).all()
    purchases = db.scalars(select(PurchaseRequest).where(PurchaseRequest.project_id == project.id if project else PurchaseRequest.id == -1).order_by(PurchaseRequest.created_at)).all()
    invoices = db.scalars(select(SalesInvoice).where(SalesInvoice.sales_order_id == order.id).order_by(SalesInvoice.invoice_date)).all()
    receivables = db.scalars(select(Receivable).where(Receivable.order_id == order.id).order_by(Receivable.due_date)).all()
    events = db.scalars(select(OrderEvent).where(OrderEvent.sales_order_id == order.id).order_by(OrderEvent.created_at.desc())).all()
    return {
        "order": row_dict(order), "customer": row_dict(customer), "contract": row_dict(contract) if contract else None,
        "project": row_dict(project) if project else None, "inventory": items, "inventory_ready": enough,
        "work_orders": [row_dict(x) for x in work_orders], "acceptances": [row_dict(x) for x in acceptances],
        "purchase_requests": [row_dict(x) for x in purchases], "invoices": [row_dict(x) for x in invoices],
        "receivables": [row_dict(x) for x in receivables], "events": [row_dict(x) for x in events],
    }


@router.post("/orders/{order_id}/items", status_code=201)
def add_order_item(order_id: int, payload: OrderLineIn, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    order = require_row(db, SalesOrder, order_id, "Không tìm thấy đơn hàng")
    if order.status != "DRAFT":
        raise HTTPException(409, "Chỉ sửa dòng hàng khi đơn ở trạng thái Draft")
    product = require_row(db, Product, payload.product_id, "Không tìm thấy sản phẩm")
    existing = db.scalar(select(SalesOrderItem).where(SalesOrderItem.sales_order_id == order.id, SalesOrderItem.product_id == product.id))
    if existing:
        existing.quantity += payload.quantity; existing.unit_price = payload.unit_price; row = existing
    else:
        row = SalesOrderItem(sales_order_id=order.id, product_id=product.id, name=product.name, **payload.model_dump(exclude={"product_id"}))
        db.add(row)
    db.flush()
    order.total_amount = Decimal(db.scalar(select(func.coalesce(func.sum(SalesOrderItem.quantity * SalesOrderItem.unit_price), 0)).where(
        SalesOrderItem.sales_order_id == order.id
    )) or 0)
    event(db, order, user, "ADD_ITEM", "Thêm dòng hàng", f"{product.sku} x {payload.quantity}"); db.commit()
    return row_dict(row)


@router.post("/orders/{order_id}/confirm")
def confirm_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    order = require_row(db, SalesOrder, order_id, "Không tìm thấy đơn hàng")
    if order.status != "DRAFT":
        raise HTTPException(409, "Chỉ xác nhận đơn Draft")
    if not db.scalar(select(func.count()).select_from(SalesOrderItem).where(SalesOrderItem.sales_order_id == order.id)):
        raise HTTPException(422, "Đơn hàng phải có ít nhất một dòng hàng")
    detail_total = Decimal(db.scalar(select(func.sum(SalesOrderItem.quantity * SalesOrderItem.unit_price)).where(
        SalesOrderItem.sales_order_id == order.id
    )) or 0)
    if detail_total != Decimal(order.total_amount):
        raise HTTPException(422, "Tổng giá trị đơn hàng không khớp tổng dòng hàng")
    order.status = "WAITING_INVENTORY"
    event(db, order, user, "CONFIRM", "Xác nhận đơn hàng", "Chuyển kiểm tra tồn kho"); db.commit()
    return row_dict(order)


@router.post("/orders/{order_id}/project", status_code=201)
def create_project(order_id: int, payload: ProjectIn, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.OPERATIONS_WRITE))):
    order = require_row(db, SalesOrder, order_id, "Không tìm thấy đơn hàng")
    if order.status == "DRAFT":
        raise HTTPException(409, "Phải xác nhận đơn hàng trước khi tạo project")
    if db.scalar(select(Project).where(Project.order_id == order.id)):
        raise HTTPException(409, "Đơn hàng đã có project")
    if db.scalar(select(Project).where(Project.code == payload.code)):
        raise HTTPException(409, "Mã project đã tồn tại")
    row = Project(code=payload.code, name=order.title, customer_id=order.customer_id, order_id=order.id,
                  status="PLANNING", manager_id=payload.manager_id, start_date=payload.start_date,
                  due_date=payload.due_date, budget_amount=order.cost_estimate)
    try:
        db.add(row); db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Đơn hàng đã có project hoặc mã project bị trùng")
    event(db, order, user, "CREATE_PROJECT", "Tạo mã triển khai", row.code); db.commit()
    return row_dict(row)


@router.post("/orders/{order_id}/reserve")
def reserve_stock(order_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.INVENTORY_WRITE))):
    order = require_row(db, SalesOrder, order_id, "Không tìm thấy đơn hàng")
    if order.status not in ["WAITING_INVENTORY", "READY_FOR_DELIVERY"]:
        raise HTTPException(409, "Đơn hàng chưa ở bước kiểm tồn")
    lines, _ = inventory_snapshot(db, order.id)
    if not lines:
        raise HTTPException(422, "Đơn hàng chưa có dòng hàng")
    shortages = [x for x in lines if not x.get("non_inventory") and x["shortage"] > 0]
    if shortages:
        raise HTTPException(409, {"message": "Tồn kho chưa đủ", "shortages": [{"sku": x["sku"], "quantity": x["shortage"]} for x in shortages]})
    for line in lines:
        if line.get("non_inventory"):
            continue
        needed = line["quantity"] - line["reserved_for_order"]
        if needed > 0:
            product = db.get(Product, line["product_id"])
            changed = db.execute(update(Product).where(
                Product.id == product.id,
                Product.quantity_on_hand - Product.reserved_quantity >= needed,
            ).values(reserved_quantity=Product.reserved_quantity + needed))
            if changed.rowcount != 1:
                raise HTTPException(409, f"Tồn {product.sku} vừa được người khác giữ")
            db.add(StockReservation(product_id=product.id, sales_order_id=order.id, quantity=needed, status="RESERVED", created_by=user.id))
    order.status = "READY_FOR_DELIVERY"
    event(db, order, user, "RESERVE_STOCK", "Giữ hàng cho đơn", "Đủ tồn kho và đã giữ chỗ"); db.commit()
    return workspace(order.id, db, user)


@router.post("/orders/{order_id}/create-purchase-requests")
def create_shortage_requests(order_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.PURCHASE_WRITE))):
    order = require_row(db, SalesOrder, order_id, "Không tìm thấy đơn hàng")
    project = db.scalar(select(Project).where(Project.order_id == order.id))
    lines, _ = inventory_snapshot(db, order.id)
    shortages = [x for x in lines if not x.get("non_inventory") and x["shortage"] > 0]
    if not shortages:
        raise HTTPException(409, "Đơn hàng không thiếu hàng")
    created = []
    for index, line in enumerate(shortages, 1):
        code = f"YCM-{order.code}-{index}"
        existing = db.scalar(select(PurchaseRequest).where(PurchaseRequest.code == code))
        if existing:
            created.append(existing); continue
        row = PurchaseRequest(code=code, department="Kỹ thuật", project_id=project.id if project else None,
                              product_id=line["product_id"], quantity=line["shortage"],
                              reason=f"Thiếu hàng cho đơn {order.code}", status="DRAFT", created_by=user.id)
        db.add(row); created.append(row)
    event(db, order, user, "CREATE_PURCHASE_REQUEST", "Tạo yêu cầu mua hàng", f"{len(created)} yêu cầu"); db.commit()
    return [row_dict(x) for x in created]


@router.post("/orders/{order_id}/issue")
def issue_stock(order_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.INVENTORY_WRITE))):
    order = require_row(db, SalesOrder, order_id, "Không tìm thấy đơn hàng")
    if order.status != "READY_FOR_DELIVERY":
        raise HTTPException(409, "Đơn hàng chưa sẵn sàng xuất kho")
    reservations = db.scalars(select(StockReservation).where(StockReservation.sales_order_id == order.id, StockReservation.status == "RESERVED")).all()
    if not reservations:
        raise HTTPException(422, "Đơn hàng chưa được giữ hàng")
    for reservation in reservations:
        product = db.get(Product, reservation.product_id)
        changed = db.execute(update(Product).where(
            Product.id == product.id, Product.quantity_on_hand >= reservation.quantity,
            Product.reserved_quantity >= reservation.quantity,
        ).values(
            quantity_on_hand=Product.quantity_on_hand - reservation.quantity,
            reserved_quantity=Product.reserved_quantity - reservation.quantity,
        ))
        if changed.rowcount != 1:
            raise HTTPException(409, f"Tồn kho {product.sku} vừa được cập nhật")
        reservation.status = "FULFILLED"
        db.add(StockMovement(product_id=product.id, movement_type="OUT", quantity=reservation.quantity,
                             reference=order.code, note=f"Xuất cho đơn {order.code}", created_by=user.id))
    order.status = "IN_IMPLEMENTATION"
    project = db.scalar(select(Project).where(Project.order_id == order.id))
    if project: project.status = "IN_PROGRESS"
    event(db, order, user, "ISSUE_STOCK", "Xuất kho triển khai", None); db.commit()
    return row_dict(order)


@router.post("/orders/{order_id}/accept")
def accept_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.OPERATIONS_APPROVE))):
    order = require_row(db, SalesOrder, order_id, "Không tìm thấy đơn hàng")
    if order.status != "IN_IMPLEMENTATION":
        raise HTTPException(409, "Đơn hàng chưa ở bước triển khai")
    project = db.scalar(select(Project).where(Project.order_id == order.id))
    if not project:
        raise HTTPException(409, "Đơn hàng chưa có Project")
    unfinished = db.scalar(select(WorkOrder.id).where(WorkOrder.project_id == project.id, WorkOrder.status != "DONE").limit(1))
    full_acceptance = db.scalar(select(AcceptanceRecord).where(
        AcceptanceRecord.project_id == project.id, AcceptanceRecord.status == "APPROVED",
        AcceptanceRecord.acceptance_type == "FULL",
    ))
    if unfinished or not full_acceptance:
        raise HTTPException(409, "Cần hoàn tất mọi Work Order và có nghiệm thu toàn bộ đã duyệt")
    order.status = "ACCEPTED"; project.status = "COMPLETED"; project.progress = 100
    event(db, order, user, "ACCEPT", "Nghiệm thu đơn hàng", None); db.commit()
    return row_dict(order)


@router.post("/orders/{order_id}/invoice", status_code=201)
def issue_invoice(order_id: int, payload: InvoiceIn, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.FINANCE_WRITE))):
    order = require_row(db, SalesOrder, order_id, "Không tìm thấy đơn hàng")
    if order.status not in ["ACCEPTED", "INVOICED", "PARTIALLY_PAID"]:
        raise HTTPException(409, "Chỉ xuất hóa đơn sau nghiệm thu")
    if db.scalar(select(SalesInvoice).where(SalesInvoice.invoice_no == payload.invoice_no)):
        raise HTTPException(409, "Số hóa đơn đã tồn tại")
    total = payload.amount_before_vat + payload.vat_amount
    changed = db.execute(update(SalesOrder).where(
        SalesOrder.id == order.id, SalesOrder.invoiced_amount + total <= SalesOrder.total_amount,
    ).values(invoiced_amount=SalesOrder.invoiced_amount + total))
    if changed.rowcount != 1:
        raise HTTPException(409, "Tổng hóa đơn vượt giá trị đơn hoặc vừa có hóa đơn khác được phát hành")
    invoice = SalesInvoice(invoice_no=payload.invoice_no, sales_order_id=order.id, customer_id=order.customer_id,
                           due_date=payload.due_date, amount_before_vat=payload.amount_before_vat,
                           vat_amount=payload.vat_amount, total_amount=total, issued_by=user.id)
    receivable = Receivable(customer_id=order.customer_id, order_id=order.id, invoice_no=payload.invoice_no,
                            amount=total, paid_amount=0, due_date=payload.due_date, status="OPEN")
    db.add_all([invoice, receivable]); order.status = "INVOICED"
    event(db, order, user, "ISSUE_INVOICE", "Phát hành hóa đơn", payload.invoice_no); db.commit()
    return row_dict(invoice)


@router.post("/orders/{order_id}/receipts", status_code=201)
def record_receipt(order_id: int, payload: ReceiptIn, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.FINANCE_WRITE))):
    row, order = receive_payment(
        db, order_id=order_id, receivable_id=payload.receivable_id, code=payload.code,
        amount=payload.amount, received_date=payload.received_date, method=payload.method,
        transaction_ref=payload.transaction_ref, note=payload.note, user_id=user.id,
    )
    event(db, order, user, "RECEIVE_PAYMENT", "Ghi nhận thu tiền", f"{payload.code}: {payload.amount}"); db.commit()
    return row_dict(row)


@router.post("/orders/{order_id}/close")
def close_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_APPROVE))):
    order = require_row(db, SalesOrder, order_id, "Không tìm thấy đơn hàng")
    if order.status != "PAID":
        raise HTTPException(409, "Chỉ đóng đơn khi đã thu đủ tiền")
    project = db.scalar(select(Project).where(Project.order_id == order.id))
    if project and project.status != "COMPLETED":
        raise HTTPException(409, "Project chưa hoàn tất")
    order.status = "CLOSED"
    if order.contract_id:
        contract = db.get(Contract, order.contract_id)
        if contract: contract.status = "COMPLETED"
    event(db, order, user, "CLOSE", "Hoàn tất đơn hàng", "Chuyển CSKH/Bảo hành"); db.commit()
    return row_dict(order)
