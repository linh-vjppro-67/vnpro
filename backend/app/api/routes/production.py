from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
import tempfile
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.config import settings
from app.core.permissions import Permission
from app.db.session import get_db
from app.models import (
    ApprovalRule, CollectionActivity, EntityAttachment, GoodsReceipt,
    GoodsReceiptLine, Notification, Opportunity, Product, PurchaseOrder,
    StockMovement, TechnicalRequest, User, WarrantyProfile,
)
from app.services import audit

router = APIRouter(prefix="/production", tags=["SRS Production"])


def as_dict(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def get_or_404(db, model, row_id, message="Không tìm thấy dữ liệu"):
    row = db.get(model, row_id)
    if not row:
        raise HTTPException(404, message)
    return row


def notify(db, role, title, message, entity_type, entity_id):
    db.add(Notification(role=role, title=title, message=message, entity_type=entity_type, entity_id=entity_id))


class TechnicalRequestIn(BaseModel):
    code: str
    opportunity_id: int | None = None
    sales_order_id: int | None = None
    ticket_id: int | None = None
    request_type: str
    scope: str
    site_address: str | None = None
    priority: str = "MEDIUM"
    sla_hours: int = Field(default=24, ge=1, le=720)
    assignee_id: int | None = None


class TechnicalAction(BaseModel):
    action: str
    note: str | None = None
    assignee_id: int | None = None


@router.get("/technical-requests")
def technical_requests(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.OPERATIONS_READ))):
    return [as_dict(x) for x in db.scalars(select(TechnicalRequest).order_by(TechnicalRequest.created_at.desc())).all()]


@router.post("/technical-requests", status_code=201)
def create_technical_request(payload: TechnicalRequestIn, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.OPERATIONS_WRITE))):
    if sum(x is not None for x in [payload.opportunity_id, payload.sales_order_id, payload.ticket_id]) != 1:
        raise HTTPException(422, "Yêu cầu kỹ thuật phải liên kết đúng một nguồn Opportunity/Order/Ticket")
    if payload.opportunity_id:
        get_or_404(db, Opportunity, payload.opportunity_id, "Không tìm thấy cơ hội")
    if db.scalar(select(TechnicalRequest).where(TechnicalRequest.code == payload.code)):
        raise HTTPException(409, "Mã yêu cầu kỹ thuật đã tồn tại")
    values = payload.model_dump(exclude={"sla_hours"})
    row = TechnicalRequest(**values, sla_due_at=datetime.now(timezone.utc) + timedelta(hours=payload.sla_hours),
                           status="ASSIGNED" if payload.assignee_id else "NEW", created_by=user.id)
    db.add(row); db.flush()
    notify(db, "TECH_SOLUTION", "Yêu cầu kỹ thuật mới", f"{row.code}: {row.scope}", "TECHNICAL_REQUEST", row.id)
    audit(db, user, "CREATE", "TECHNICAL_REQUEST", row.id, row.code); db.commit()
    return as_dict(row)


@router.post("/technical-requests/{row_id}/action")
def technical_request_action(row_id: int, payload: TechnicalAction, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.OPERATIONS_WRITE))):
    row = get_or_404(db, TechnicalRequest, row_id, "Không tìm thấy yêu cầu kỹ thuật")
    action = payload.action.upper()
    transitions = {
        ("NEW", "ASSIGN"): "ASSIGNED", ("ASSIGNED", "ACCEPT"): "IN_PROGRESS",
        ("IN_PROGRESS", "REQUEST_INFO"): "NEED_INFO", ("NEED_INFO", "RESUME"): "IN_PROGRESS",
        ("IN_PROGRESS", "COMPLETE"): "COMPLETED", ("NEW", "CANCEL"): "CANCELLED",
        ("ASSIGNED", "CANCEL"): "CANCELLED",
    }
    target = transitions.get((row.status, action))
    if not target:
        raise HTTPException(409, "Chuyển trạng thái yêu cầu kỹ thuật không hợp lệ")
    if action == "ASSIGN":
        if not payload.assignee_id:
            raise HTTPException(422, "Bắt buộc chọn kỹ thuật phụ trách")
        get_or_404(db, User, payload.assignee_id, "Không tìm thấy kỹ thuật viên")
        row.assignee_id = payload.assignee_id
    if action == "COMPLETE":
        if not payload.note:
            raise HTTPException(422, "Bắt buộc nhập kết quả hoàn thành")
        row.result_note = payload.note
    row.status = target
    audit(db, user, action, "TECHNICAL_REQUEST", row.id, payload.note or ""); db.commit()
    return as_dict(row)


class ApprovalRuleIn(BaseModel):
    document_type: str
    name: str
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None
    max_discount_percent: Decimal | None = None
    min_margin_percent: Decimal | None = None
    over_budget: bool | None = None
    approver_role: str
    step_no: int = Field(default=1, ge=1)
    sla_hours: int = Field(default=24, ge=1)


@router.get("/approval-rules")
def approval_rules(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.USERS_MANAGE))):
    return [as_dict(x) for x in db.scalars(select(ApprovalRule).order_by(ApprovalRule.document_type, ApprovalRule.step_no)).all()]


@router.post("/approval-rules", status_code=201)
def create_approval_rule(payload: ApprovalRuleIn, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.USERS_MANAGE))):
    row = ApprovalRule(**payload.model_dump())
    db.add(row); db.flush(); audit(db, user, "CREATE", "APPROVAL_RULE", row.id, row.name); db.commit()
    return as_dict(row)


ALLOWED_MIME = {
    "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "image/jpeg", "image/png",
}
ENTITY_MODELS = {
    "QUOTATION": ("app.models", "Quotation"),
    "CONTRACT": ("app.models", "Contract"),
    "SALES_ORDER": ("app.models", "SalesOrder"),
    "PROJECT": ("app.models", "Project"),
    "WORK_ORDER": ("app.models", "WorkOrder"),
    "ACCEPTANCE_RECORD": ("app.models", "AcceptanceRecord"),
    "EXPENSE": ("app.models", "Expense"),
    "GOODS_RECEIPT": ("app.models", "GoodsReceipt"),
    "SUPPORT_TICKET": ("app.models", "SupportTicket"),
}
ENTITY_PERMISSIONS = {
    "QUOTATION": Permission.SALES_WRITE, "CONTRACT": Permission.SALES_WRITE,
    "SALES_ORDER": Permission.SALES_WRITE, "PROJECT": Permission.OPERATIONS_WRITE,
    "WORK_ORDER": Permission.OPERATIONS_WRITE, "ACCEPTANCE_RECORD": Permission.OPERATIONS_WRITE,
    "EXPENSE": Permission.COST_WRITE, "GOODS_RECEIPT": Permission.INVENTORY_WRITE,
    "SUPPORT_TICKET": Permission.SUPPORT_WRITE,
}


def normalized_entity(entity_type: str) -> str:
    value = entity_type.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,49}", value) or value not in ENTITY_MODELS:
        raise HTTPException(422, "Loại hồ sơ không được hỗ trợ")
    return value


def detect_mime(content: bytes) -> str | None:
    if content.startswith(b"%PDF-"): return "application/pdf"
    if content.startswith(b"\x89PNG\r\n\x1a\n"): return "image/png"
    if content.startswith(b"\xff\xd8\xff"): return "image/jpeg"
    if content.startswith(b"PK\x03\x04"): return "application/zip"
    return None


@router.get("/attachments/{entity_type}/{entity_id}")
def attachments(entity_type: str, entity_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.DASHBOARD_READ))):
    entity_type = normalized_entity(entity_type)
    rows = db.scalars(select(EntityAttachment).where(
        EntityAttachment.entity_type == entity_type.upper(), EntityAttachment.entity_id == entity_id,
        EntityAttachment.is_active,
    ).order_by(EntityAttachment.document_type, EntityAttachment.version_no.desc())).all()
    return [as_dict(x) for x in rows]


@router.post("/attachments/{entity_type}/{entity_id}", status_code=201)
async def upload_attachment(
    entity_type: str, entity_id: int, document_type: str = Form(...), file: UploadFile = File(...),
    db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.DASHBOARD_READ)),
):
    entity_type = normalized_entity(entity_type)
    from app.core.permissions import has_permission
    if not has_permission(user.role, ENTITY_PERMISSIONS[entity_type]):
        raise HTTPException(403, "Không có quyền tải hồ sơ cho đối tượng này")
    module_name, model_name = ENTITY_MODELS[entity_type]
    import importlib
    model = getattr(importlib.import_module(module_name), model_name)
    if not db.get(model, entity_id):
        raise HTTPException(404, "Đối tượng gắn hồ sơ không tồn tại")
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(413, "Tệp vượt dung lượng cho phép")
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(415, "Định dạng tệp không được hỗ trợ")
    detected = detect_mime(content)
    expected = "application/zip" if file.content_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    } else file.content_type
    if detected != expected:
        raise HTTPException(415, "Nội dung tệp không khớp định dạng khai báo")
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", file.filename or "attachment")
    root = Path(settings.upload_dir).resolve()
    target_dir = (root / entity_type.lower() / str(entity_id)).resolve()
    if root not in target_dir.parents:
        raise HTTPException(422, "Đường dẫn hồ sơ không hợp lệ")
    target_dir.mkdir(parents=True, exist_ok=True)
    current = db.scalar(select(func.max(EntityAttachment.version_no)).where(
        EntityAttachment.entity_type == entity_type.upper(), EntityAttachment.entity_id == entity_id,
        EntityAttachment.document_type == document_type,
    )) or 0
    target = target_dir / f"v{current + 1}_{safe_name}"
    fd, temp_name = tempfile.mkstemp(prefix=".upload-", dir=target_dir)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise
    row = EntityAttachment(entity_type=entity_type.upper(), entity_id=entity_id, document_type=document_type,
                           file_name=file.filename or safe_name, storage_path=str(target), mime_type=file.content_type,
                           file_size=len(content), version_no=current + 1, uploaded_by=user.id)
    try:
        db.add(row); db.flush()
        audit(db, user, "UPLOAD", "ATTACHMENT", row.id, f"{entity_type}#{entity_id} {document_type}")
        db.commit()
        os.replace(temp_name, target)
    except Exception:
        db.rollback()
        Path(temp_name).unlink(missing_ok=True)
        if row.id:
            db.query(EntityAttachment).filter(EntityAttachment.id == row.id).delete()
            db.commit()
        raise
    return as_dict(row)


class ReceiptLineIn(BaseModel):
    product_id: int
    received_quantity: int = Field(gt=0)
    accepted_quantity: int = Field(ge=0)
    quarantine_quantity: int = Field(default=0, ge=0)
    rejected_quantity: int = Field(default=0, ge=0)
    quality_note: str | None = None


class GoodsReceiptIn(BaseModel):
    code: str
    purchase_order_id: int
    received_date: date
    delivery_note: str | None = None
    document_checklist: dict[str, bool]
    lines: list[ReceiptLineIn] = Field(min_length=1)


@router.get("/goods-receipts")
def goods_receipts(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.INVENTORY_READ))):
    return [{**as_dict(x), "lines": [as_dict(line) for line in x.lines]} for x in db.scalars(select(GoodsReceipt).order_by(GoodsReceipt.created_at.desc())).all()]


@router.post("/goods-receipts", status_code=201)
def create_goods_receipt(payload: GoodsReceiptIn, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.INVENTORY_WRITE))):
    po = db.scalar(select(PurchaseOrder).where(PurchaseOrder.id == payload.purchase_order_id).with_for_update())
    if not po:
        raise HTTPException(404, "Không tìm thấy PO")
    if po.status not in {"ORDERED", "PARTIALLY_RECEIVED"}:
        raise HTTPException(409, "Chỉ nhận hàng từ PO đã đặt hoặc đang nhận một phần")
    if db.scalar(select(GoodsReceipt).where(GoodsReceipt.code == payload.code)):
        raise HTTPException(409, "Mã phiếu nhập đã tồn tại")
    if not payload.document_checklist or not all(payload.document_checklist.values()):
        raise HTTPException(422, "Bộ chứng từ nhập hàng chưa đầy đủ")
    po_quantities = {line.product_id: line.quantity for line in po.items}
    if len({line.product_id for line in payload.lines}) != len(payload.lines):
        raise HTTPException(422, "Một sản phẩm chỉ được xuất hiện một lần trong phiếu nhập")
    for line in payload.lines:
        if line.accepted_quantity + line.quarantine_quantity + line.rejected_quantity != line.received_quantity:
            raise HTTPException(422, "Tổng đạt + quarantine + từ chối phải bằng số nhận")
        if line.product_id not in po_quantities:
            raise HTTPException(422, "Sản phẩm nhận không nằm trong PO")
        previously_accepted = db.scalar(
            select(func.coalesce(func.sum(GoodsReceiptLine.accepted_quantity + GoodsReceiptLine.quarantine_quantity), 0))
            .join(GoodsReceipt, GoodsReceipt.id == GoodsReceiptLine.goods_receipt_id)
            .where(
                GoodsReceipt.purchase_order_id == po.id,
                GoodsReceipt.status.in_(["INSPECTED", "POSTED"]),
                GoodsReceiptLine.product_id == line.product_id,
            )
        ) or 0
        remaining = po_quantities[line.product_id] - int(previously_accepted)
        if line.accepted_quantity + line.quarantine_quantity > remaining:
            raise HTTPException(422, f"Số lượng đạt/cách ly vượt số còn lại trên PO ({remaining})")
        get_or_404(db, Product, line.product_id, "Không tìm thấy sản phẩm")
    values = payload.model_dump(exclude={"lines", "document_checklist"})
    row = GoodsReceipt(**values, supplier_id=po.supplier_id,
                       document_checklist=json.dumps(payload.document_checklist, ensure_ascii=False),
                       status="INSPECTED", created_by=user.id)
    row.lines = [GoodsReceiptLine(**x.model_dump()) for x in payload.lines]
    db.add(row); db.flush(); audit(db, user, "CREATE", "GOODS_RECEIPT", row.id, row.code); db.commit()
    return {**as_dict(row), "lines": [as_dict(x) for x in row.lines]}


@router.post("/goods-receipts/{row_id}/post")
def post_goods_receipt(row_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.INVENTORY_WRITE))):
    row = get_or_404(db, GoodsReceipt, row_id, "Không tìm thấy phiếu nhập")
    if row.status != "INSPECTED":
        raise HTTPException(409, "Phiếu nhập không ở trạng thái chờ Post")
    po = db.scalar(select(PurchaseOrder).where(PurchaseOrder.id == row.purchase_order_id).with_for_update())
    for line in row.lines:
        product = db.scalar(select(Product).where(Product.id == line.product_id).with_for_update())
        db.execute(update(Product).where(Product.id == product.id).values(
            quantity_on_hand=Product.quantity_on_hand + line.accepted_quantity,
            quarantine_quantity=Product.quarantine_quantity + line.quarantine_quantity,
        ))
        if line.accepted_quantity:
            db.add(StockMovement(product_id=product.id, movement_type="IN", quantity=line.accepted_quantity,
                                 reference=row.code, note="Goods Receipt đạt kiểm định", created_by=user.id))
    row.status = "POSTED"; row.posted_by = user.id
    db.flush()
    ordered = {line.product_id: line.quantity for line in po.items}
    received_rows = db.execute(
        select(
            GoodsReceiptLine.product_id,
            func.sum(GoodsReceiptLine.accepted_quantity + GoodsReceiptLine.quarantine_quantity),
        ).join(GoodsReceipt, GoodsReceipt.id == GoodsReceiptLine.goods_receipt_id)
        .where(GoodsReceipt.purchase_order_id == po.id, GoodsReceipt.status == "POSTED")
        .group_by(GoodsReceiptLine.product_id)
    ).all()
    received = {product_id: int(quantity) for product_id, quantity in received_rows}
    po.status = "FULLY_RECEIVED" if all(received.get(product_id, 0) >= quantity for product_id, quantity in ordered.items()) else "PARTIALLY_RECEIVED"
    audit(db, user, "POST", "GOODS_RECEIPT", row.id, row.code); db.commit()
    return as_dict(row)


class CollectionIn(BaseModel):
    activity_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    channel: str
    result: str
    promised_date: date | None = None
    promised_amount: Decimal | None = None
    next_follow_up: date | None = None


@router.get("/collections")
def collections(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.FINANCE_READ))):
    return [as_dict(x) for x in db.scalars(select(CollectionActivity).order_by(CollectionActivity.activity_date.desc())).all()]


@router.post("/receivables/{receivable_id}/collections", status_code=201)
def create_collection(receivable_id: int, payload: CollectionIn, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.FINANCE_WRITE))):
    from app.models import Receivable
    receivable = get_or_404(db, Receivable, receivable_id, "Không tìm thấy khoản phải thu")
    row = CollectionActivity(receivable_id=receivable.id, created_by=user.id, **payload.model_dump())
    db.add(row); db.flush(); audit(db, user, "FOLLOW_UP", "RECEIVABLE", receivable.id, payload.result); db.commit()
    return as_dict(row)


class WarrantyIn(BaseModel):
    code: str
    customer_id: int
    sales_order_id: int
    product_id: int | None = None
    serial_no: str | None = None
    start_date: date
    end_date: date
    coverage: str
    exclusions: str | None = None


@router.get("/warranties")
def warranties(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.SUPPORT_READ))):
    return [as_dict(x) for x in db.scalars(select(WarrantyProfile).order_by(WarrantyProfile.end_date)).all()]


@router.post("/warranties", status_code=201)
def create_warranty(payload: WarrantyIn, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SUPPORT_WRITE))):
    if payload.end_date < payload.start_date:
        raise HTTPException(422, "Ngày hết hạn phải sau ngày bắt đầu")
    if db.scalar(select(WarrantyProfile).where(WarrantyProfile.code == payload.code)):
        raise HTTPException(409, "Mã bảo hành đã tồn tại")
    from app.models import Customer, SalesOrder, SalesOrderItem
    customer = get_or_404(db, Customer, payload.customer_id, "Không tìm thấy khách hàng")
    order = get_or_404(db, SalesOrder, payload.sales_order_id, "Không tìm thấy đơn hàng")
    if order.customer_id != customer.id:
        raise HTTPException(422, "Đơn hàng không thuộc khách hàng đã chọn")
    if order.status not in {"ACCEPTED", "INVOICED", "PARTIALLY_PAID", "PAID", "CLOSED"}:
        raise HTTPException(409, "Chỉ tạo bảo hành sau khi đơn đã nghiệm thu")
    if payload.product_id:
        get_or_404(db, Product, payload.product_id, "Không tìm thấy sản phẩm")
        if not db.scalar(select(SalesOrderItem.id).where(
            SalesOrderItem.sales_order_id == order.id, SalesOrderItem.product_id == payload.product_id,
            SalesOrderItem.fulfilled_quantity > 0,
        )):
            raise HTTPException(422, "Sản phẩm chưa được giao trong đơn hàng")
    row = WarrantyProfile(**payload.model_dump())
    db.add(row); db.flush(); audit(db, user, "CREATE", "WARRANTY", row.id, row.code); db.commit()
    return as_dict(row)


@router.get("/notifications")
def notifications(db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.DASHBOARD_READ))):
    rows = db.scalars(select(Notification).where(
        (Notification.user_id == user.id) | (Notification.role == user.role)
    ).order_by(Notification.created_at.desc()).limit(100)).all()
    return [as_dict(x) for x in rows]


@router.post("/notifications/{notification_id}/read")
def read_notification(notification_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.DASHBOARD_READ))):
    row = get_or_404(db, Notification, notification_id, "Không tìm thấy thông báo")
    if row.user_id not in [None, user.id] and row.role != user.role:
        raise HTTPException(403, "Không có quyền xem thông báo")
    row.is_read = True; db.commit()
    return as_dict(row)
