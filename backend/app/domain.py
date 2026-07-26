"""Shared transactional business rules used by every API surface."""
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import PaymentReceipt, Project, Receivable, SalesOrder


def locked(db: Session, model, row_id: int):
    """Lock on PostgreSQL; SQLite serializes the following write transaction."""
    row = db.scalar(select(model).where(model.id == row_id).with_for_update())
    if not row:
        raise HTTPException(404, "Không tìm thấy dữ liệu")
    return row


def sync_order_payment_status(db: Session, order: SalesOrder) -> Decimal:
    db.flush()
    remaining = Decimal(db.scalar(
        select(func.coalesce(func.sum(Receivable.amount - Receivable.paid_amount), 0))
        .where(Receivable.order_id == order.id)
    ) or 0)
    invoiced = Decimal(db.scalar(
        select(func.coalesce(func.sum(Receivable.amount), 0)).where(Receivable.order_id == order.id)
    ) or 0)
    if invoiced == 0:
        order.payment_status = "UNPAID"
    elif remaining == 0:
        order.payment_status = "PAID"
        order.status = "PAID"
    elif remaining < invoiced:
        order.payment_status = "PARTIAL"
        order.status = "PARTIALLY_PAID"
    else:
        order.payment_status = "UNPAID"
        if order.status in {"PARTIALLY_PAID", "PAID"}:
            order.status = "INVOICED"
    return remaining


def receive_payment(
    db: Session, *, order_id: int, receivable_id: int, code: str, amount: Decimal,
    received_date, method: str, transaction_ref: str | None, note: str | None, user_id: int,
) -> tuple[PaymentReceipt, SalesOrder]:
    order = locked(db, SalesOrder, order_id)
    receivable = locked(db, Receivable, receivable_id)
    if receivable.order_id != order.id:
        raise HTTPException(422, "Khoản phải thu không thuộc đơn hàng")
    if receivable.status == "PAID" or Decimal(receivable.paid_amount) + amount > Decimal(receivable.amount):
        raise HTTPException(422, "Số thu vượt công nợ còn lại")
    existing = db.scalar(select(PaymentReceipt).where(PaymentReceipt.code == code))
    if existing:
        raise HTTPException(409, "Mã phiếu thu đã tồn tại")
    receipt = PaymentReceipt(
        code=code, receivable_id=receivable.id, sales_order_id=order.id,
        amount=amount, received_date=received_date, method=method,
        transaction_ref=transaction_ref, note=note, received_by=user_id,
    )
    db.add(receipt)
    changed = db.execute(update(Receivable).where(
        Receivable.id == receivable.id, Receivable.status != "PAID",
        Receivable.paid_amount + amount <= Receivable.amount,
    ).values(paid_amount=Receivable.paid_amount + amount))
    if changed.rowcount != 1:
        raise HTTPException(409, "Công nợ vừa được cập nhật bởi giao dịch khác")
    db.refresh(receivable)
    receivable.status = "PAID" if receivable.paid_amount == receivable.amount else "PARTIAL"
    sync_order_payment_status(db, order)
    return receipt, order


def add_project_actual_cost(db: Session, project_id: int | None, amount: Decimal) -> None:
    if not project_id:
        return
    changed = db.execute(update(Project).where(Project.id == project_id).values(actual_cost=Project.actual_cost + amount))
    if changed.rowcount != 1:
        raise HTTPException(409, "Project không tồn tại hoặc vừa được cập nhật")
