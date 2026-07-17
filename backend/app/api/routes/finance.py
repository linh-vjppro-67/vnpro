from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models import Receivable, User
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
    item.paid_amount = item.paid_amount + payload.paid_amount
    if item.paid_amount >= item.amount:
        item.status = "PAID"
    elif item.paid_amount > 0:
        item.status = "PARTIAL"
    audit(db, user, "PAYMENT", "RECEIVABLE", item.id, f"Paid {payload.paid_amount}")
    db.commit(); db.refresh(item)
    return item
