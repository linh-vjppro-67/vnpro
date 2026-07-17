from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.api.deps import require_permission
from app.approvals import decide_approval, request_approval, resolve_user_by_role
from app.core.permissions import Permission
from app.core.workflow import DECISION_TARGETS, assert_transition
from app.db.session import get_db
from app.models import ApprovalRequest, Product, PurchaseOrder, PurchaseOrderItem, PurchaseRequest, StockMovement, Supplier, User
from app.schemas import (
    DecisionNote, PurchaseOrderCreate, PurchaseOrderOut, PurchaseRequestCreate, PurchaseRequestOut,
    SupplierCreate, SupplierOut,
)
from app.services import audit

router = APIRouter(prefix="/purchasing", tags=["Purchasing"])


def _pending_approval(db: Session, entity_type: str, entity_id: int) -> ApprovalRequest | None:
    return db.scalar(select(ApprovalRequest).where(ApprovalRequest.entity_type == entity_type, ApprovalRequest.entity_id == entity_id, ApprovalRequest.status == "PENDING"))


def _decide(db: Session, entity_type: str, entity, user: User, approve: bool, note: str | None):
    approval = _pending_approval(db, entity_type, entity.id)
    if not approval:
        raise HTTPException(404, "Không có yêu cầu phê duyệt đang chờ xử lý")
    if approval.approver_id and approval.approver_id != user.id and user.role not in {"DIRECTOR", "SYSTEM_ADMIN"}:
        raise HTTPException(403, "Bạn không phải người được giao phê duyệt yêu cầu này")
    targets = DECISION_TARGETS[entity_type]
    try:
        decide_approval(db, approval=approval, entity=entity, decided_by=user, approve=approve, note=note, approved_status=targets["approved"], rejected_status=targets["rejected"])
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    db.commit(); db.refresh(entity)


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------

@router.get("/suppliers", response_model=list[SupplierOut])
def suppliers(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.PURCHASE_READ))):
    return db.scalars(select(Supplier).order_by(Supplier.name)).all()


@router.post("/suppliers", response_model=SupplierOut, status_code=201)
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.PURCHASE_WRITE))):
    if db.scalar(select(Supplier).where(Supplier.code == payload.code)):
        raise HTTPException(409, "Mã nhà cung cấp đã tồn tại")
    item = Supplier(**payload.model_dump())
    db.add(item); db.flush(); audit(db, user, "CREATE", "SUPPLIER", item.id, item.name); db.commit(); db.refresh(item)
    return item


# ---------------------------------------------------------------------------
# Purchase requests (yêu cầu mua hàng)
# ---------------------------------------------------------------------------

@router.get("/requests", response_model=list[PurchaseRequestOut])
def purchase_requests(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.PURCHASE_READ))):
    return db.scalars(select(PurchaseRequest).order_by(PurchaseRequest.created_at.desc())).all()


@router.post("/requests", response_model=PurchaseRequestOut, status_code=201)
def create_purchase_request(payload: PurchaseRequestCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.PURCHASE_WRITE))):
    if db.scalar(select(PurchaseRequest).where(PurchaseRequest.code == payload.code)):
        raise HTTPException(409, "Mã yêu cầu mua hàng đã tồn tại")
    if not db.get(Product, payload.product_id):
        raise HTTPException(404, "Không tìm thấy sản phẩm")
    item = PurchaseRequest(**payload.model_dump(), status="DRAFT", created_by=user.id)
    db.add(item); db.flush(); audit(db, user, "CREATE", "PURCHASE_REQUEST", item.id, item.code); db.commit(); db.refresh(item)
    return item


@router.post("/requests/{request_id}/submit", response_model=PurchaseRequestOut)
def submit_purchase_request(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.PURCHASE_WRITE))):
    item = db.get(PurchaseRequest, request_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy yêu cầu mua hàng")
    assert_transition("PURCHASE_REQUEST", item.status, "SUBMITTED")
    director = resolve_user_by_role(db, "DIRECTOR")
    request_approval(db, entity_type="PURCHASE_REQUEST", entity=item, requested_by=user, approver_id=director.id if director else None, reason=None, pending_status="SUBMITTED")
    db.commit(); db.refresh(item)
    return item


@router.post("/requests/{request_id}/approve", response_model=PurchaseRequestOut)
def approve_purchase_request(request_id: int, payload: DecisionNote, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.PURCHASE_APPROVE))):
    item = db.get(PurchaseRequest, request_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy yêu cầu mua hàng")
    _decide(db, "PURCHASE_REQUEST", item, user, True, payload.note)
    return item


@router.post("/requests/{request_id}/reject", response_model=PurchaseRequestOut)
def reject_purchase_request(request_id: int, payload: DecisionNote, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.PURCHASE_APPROVE))):
    item = db.get(PurchaseRequest, request_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy yêu cầu mua hàng")
    _decide(db, "PURCHASE_REQUEST", item, user, False, payload.note)
    return item


@router.post("/requests/{request_id}/convert-to-order", response_model=PurchaseOrderOut, status_code=201)
def convert_purchase_request_to_order(request_id: int, payload: PurchaseOrderCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.PURCHASE_WRITE))):
    request_item = db.get(PurchaseRequest, request_id)
    if not request_item:
        raise HTTPException(404, "Không tìm thấy yêu cầu mua hàng")
    assert_transition("PURCHASE_REQUEST", request_item.status, "CONVERTED")
    if db.scalar(select(PurchaseOrder).where(PurchaseOrder.code == payload.code)):
        raise HTTPException(409, "Mã đơn mua hàng đã tồn tại")
    data = payload.model_dump(exclude={"items", "purchase_request_id"})
    order = PurchaseOrder(**data, purchase_request_id=request_item.id, status="DRAFT", created_by=user.id)
    if payload.items:
        order.items = [PurchaseOrderItem(**i.model_dump()) for i in payload.items]
    else:
        order.items = [PurchaseOrderItem(product_id=request_item.product_id, quantity=request_item.quantity, unit_price=request_item.product.cost_price)]
    order.total_amount = sum((i.quantity * i.unit_price for i in order.items), Decimal(0))
    db.add(order); db.flush()
    request_item.status = "CONVERTED"
    audit(db, user, "CONVERT", "PURCHASE_REQUEST", request_item.id, f"-> PURCHASE_ORDER {order.code}")
    db.commit(); db.refresh(order)
    return order


# ---------------------------------------------------------------------------
# Purchase orders
# ---------------------------------------------------------------------------

@router.get("/orders", response_model=list[PurchaseOrderOut])
def purchase_orders(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.PURCHASE_READ))):
    return db.scalars(select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).order_by(PurchaseOrder.created_at.desc())).all()


@router.post("/orders", response_model=PurchaseOrderOut, status_code=201)
def create_purchase_order(payload: PurchaseOrderCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.PURCHASE_WRITE))):
    if db.scalar(select(PurchaseOrder).where(PurchaseOrder.code == payload.code)):
        raise HTTPException(409, "Mã đơn mua hàng đã tồn tại")
    if not db.get(Supplier, payload.supplier_id):
        raise HTTPException(404, "Không tìm thấy nhà cung cấp")
    data = payload.model_dump(exclude={"items"})
    order = PurchaseOrder(**data, status="DRAFT", created_by=user.id)
    order.items = [PurchaseOrderItem(**i.model_dump()) for i in payload.items]
    order.total_amount = sum((i.quantity * i.unit_price for i in order.items), Decimal(0))
    db.add(order); db.flush(); audit(db, user, "CREATE", "PURCHASE_ORDER", order.id, order.code); db.commit(); db.refresh(order)
    return order


@router.post("/orders/{order_id}/place", response_model=PurchaseOrderOut)
def place_purchase_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.PURCHASE_WRITE))):
    item = db.get(PurchaseOrder, order_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy đơn mua hàng")
    assert_transition("PURCHASE_ORDER", item.status, "ORDERED")
    item.status = "ORDERED"
    audit(db, user, "PLACE", "PURCHASE_ORDER", item.id, item.code)
    db.commit(); db.refresh(item)
    return item


@router.post("/orders/{order_id}/receive", response_model=PurchaseOrderOut)
def receive_purchase_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.PURCHASE_WRITE))):
    item = db.scalar(select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).where(PurchaseOrder.id == order_id))
    if not item:
        raise HTTPException(404, "Không tìm thấy đơn mua hàng")
    assert_transition("PURCHASE_ORDER", item.status, "RECEIVED")
    for line in item.items:
        product = db.get(Product, line.product_id)
        product.quantity_on_hand += line.quantity
        db.add(StockMovement(product_id=product.id, movement_type="IN", quantity=line.quantity, reference=item.code, note=f"Nhập kho từ PO {item.code}", created_by=user.id))
    item.status = "RECEIVED"
    audit(db, user, "RECEIVE", "PURCHASE_ORDER", item.id, item.code)
    db.commit(); db.refresh(item)
    return item
