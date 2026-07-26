from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models import Receivable, User
from app.domain import receive_payment
from app.schemas import ReceivableOut, ReceivableCreate, ReceivablePayment
from app.services import audit

router = APIRouter(prefix="/finance", tags=["Finance"])


@router.get("/receivables", response_model=list[ReceivableOut])
def receivables(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.FINANCE_READ))):
    return db.scalars(select(Receivable).order_by(Receivable.due_date.asc())).all()


@router.post("/receivables", response_model=ReceivableOut, status_code=201)
def create_receivable(payload: ReceivableCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.FINANCE_WRITE))):
    receivable = Receivable(**payload.model_dump(), status="OPEN", paid_amount=0)
    db.add(receivable); db.flush(); audit(db, user, "CREATE", "RECEIVABLE", receivable.id, receivable.invoice_no)
    db.commit(); db.refresh(receivable)
    return receivable


@router.patch("/receivables/{receivable_id}/payment", response_model=ReceivableOut)
def pay_receivable(receivable_id: int, payload: ReceivablePayment, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.FINANCE_WRITE))):
    item = db.get(Receivable, receivable_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy công nợ")
    if payload.paid_amount <= 0:
        raise HTTPException(422, "Số tiền thu phải lớn hơn 0")
    if item.status == "PAID" or item.paid_amount + payload.paid_amount > item.amount:
        raise HTTPException(422, "Số tiền thu vượt số dư phải thu")
    if not item.order_id:
        raise HTTPException(422, "Khoản phải thu phải liên kết Sales Order để thu tiền")
    _, order = receive_payment(
        db, order_id=item.order_id, receivable_id=item.id, code=payload.code,
        amount=payload.paid_amount, received_date=payload.received_date, method=payload.method,
        transaction_ref=payload.transaction_ref, note=payload.note, user_id=user.id,
    )
    audit(db, user, "PAYMENT", "RECEIVABLE", item.id, f"{payload.code}: {payload.paid_amount}; order={order.code}")
    db.commit(); db.refresh(item); return item
