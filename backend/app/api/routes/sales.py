from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models import Customer, Opportunity, SalesOrder, Receivable, User
from app.schemas import CustomerCreate, CustomerOut, OpportunityCreate, OpportunityOut, OrderCreate, OrderOut, OrderUpdate, ReceivableCreate, ReceivableOut
from app.services import audit

router = APIRouter(prefix="/sales", tags=["Sales"])


@router.get("/customers", response_model=list[CustomerOut])
def customers(q: str | None = Query(default=None), db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.SALES_READ))):
    stmt = select(Customer).order_by(Customer.created_at.desc())
    if q:
        stmt = stmt.where(or_(Customer.name.ilike(f"%{q}%"), Customer.code.ilike(f"%{q}%")))
    return db.scalars(stmt).all()


@router.post("/customers", response_model=CustomerOut, status_code=201)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    if db.scalar(select(Customer).where(Customer.code == payload.code)):
        raise HTTPException(409, "Mã khách hàng đã tồn tại")
    item = Customer(**payload.model_dump(), owner_id=user.id)
    db.add(item); db.flush(); audit(db, user, "CREATE", "CUSTOMER", item.id, item.name); db.commit(); db.refresh(item)
    return item


@router.get("/opportunities", response_model=list[OpportunityOut])
def opportunities(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.SALES_READ))):
    return db.scalars(select(Opportunity).order_by(Opportunity.created_at.desc())).all()


@router.post("/opportunities", response_model=OpportunityOut, status_code=201)
def create_opportunity(payload: OpportunityCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    item = Opportunity(**payload.model_dump(), owner_id=user.id)
    db.add(item); db.flush(); audit(db, user, "CREATE", "OPPORTUNITY", item.id, item.title); db.commit(); db.refresh(item)
    return item


@router.get("/orders", response_model=list[OrderOut])
def orders(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.SALES_READ))):
    return db.scalars(select(SalesOrder).order_by(SalesOrder.created_at.desc())).all()


@router.post("/orders", response_model=OrderOut, status_code=201)
def create_order(payload: OrderCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    item = SalesOrder(**payload.model_dump(), created_by=user.id)
    db.add(item); db.flush(); audit(db, user, "CREATE", "SALES_ORDER", item.id, item.code); db.commit(); db.refresh(item)
    return item


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.SALES_READ))):
    item = db.get(SalesOrder, order_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy đơn hàng")
    return item


@router.patch("/orders/{order_id}", response_model=OrderOut)
def update_order(order_id: int, payload: OrderUpdate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    item = db.get(SalesOrder, order_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy đơn hàng")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(item, key, value)
    audit(db, user, "UPDATE", "SALES_ORDER", item.id, f"Updated fields: {', '.join(data.keys())}")
    db.commit(); db.refresh(item)
    return item


@router.post("/orders/{order_id}/confirm", response_model=OrderOut)
def confirm_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SALES_WRITE))):
    item = db.get(SalesOrder, order_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy đơn hàng")
    if item.status != "DRAFT":
        raise HTTPException(409, "Đơn hàng chỉ có thể xác nhận khi đang ở trạng thái DRAFT")
    item.status = "CONFIRMED"
    audit(db, user, "CONFIRM", "SALES_ORDER", item.id, item.code)
    db.commit(); db.refresh(item)
    return item


@router.post("/orders/{order_id}/invoice", response_model=ReceivableOut, status_code=201)
def invoice_order(order_id: int, payload: ReceivableCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.FINANCE_WRITE))):
    order = db.get(SalesOrder, order_id)
    if not order:
        raise HTTPException(404, "Không tìm thấy đơn hàng")
    new_receivable = Receivable(**payload.model_dump(), order_id=order.id, status="OPEN", paid_amount=0)
    db.add(new_receivable); db.flush(); audit(db, user, "CREATE", "RECEIVABLE", new_receivable.id, new_receivable.invoice_no)
    db.commit(); db.refresh(new_receivable)
    return new_receivable
