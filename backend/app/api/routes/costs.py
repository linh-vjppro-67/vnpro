from fastapi import APIRouter, Depends, HTTPException
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models import Budget, Expense, ExpensePayment, User
from app.domain import add_project_actual_cost
from app.schemas import BudgetOut, ExpenseCreate, ExpenseOut
from app.services import audit

router = APIRouter(prefix="/costs", tags=["Cost management"])


class ExpensePaymentIn(BaseModel):
    paid_date: date
    amount: Decimal = Field(gt=0)
    method: str = "BANK_TRANSFER"
    transaction_ref: str | None = None


@router.get("/budgets", response_model=list[BudgetOut])
def budgets(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.COST_READ))):
    return db.scalars(select(Budget).order_by(Budget.department, Budget.period)).all()


@router.get("/expenses", response_model=list[ExpenseOut])
def expenses(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.COST_READ))):
    return db.scalars(select(Expense).order_by(Expense.expense_date.desc(), Expense.created_at.desc())).all()


@router.post("/expenses", response_model=ExpenseOut, status_code=201)
def create_expense(payload: ExpenseCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.COST_WRITE))):
    if payload.budget_id:
        budget = db.get(Budget, payload.budget_id)
        if not budget or budget.status != "APPROVED":
            raise HTTPException(422, "Ngân sách không hợp lệ")
        if budget.department != payload.department:
            raise HTTPException(422, "Ngân sách không thuộc phòng ban đề nghị")
    item = Expense(**payload.model_dump(), created_by=user.id, status="DRAFT")
    db.add(item); db.flush(); audit(db, user, "CREATE", "EXPENSE", item.id, item.description); db.commit(); db.refresh(item)
    return item


@router.post("/expenses/{expense_id}/submit", response_model=ExpenseOut)
def submit_expense(expense_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.COST_WRITE))):
    item = db.get(Expense, expense_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy đề nghị chi")
    if item.status not in ["DRAFT", "REJECTED"]:
        raise HTTPException(409, "Đề nghị chi không thể submit ở trạng thái hiện tại")
    if item.budget_id:
        budget = db.scalar(select(Budget).where(Budget.id == item.budget_id).with_for_update())
    else:
        budget = db.scalar(select(Budget).where(
            Budget.department == item.department, Budget.status == "APPROVED"
        ).order_by(Budget.period.desc()).with_for_update())
        if budget:
            item.budget_id = budget.id
    if not budget:
        raise HTTPException(422, "Không tìm thấy ngân sách được duyệt cho đề nghị")
    remaining = Decimal(budget.amount) - Decimal(budget.spent_amount) - Decimal(budget.committed_amount)
    item.status = "SUBMITTED" if item.amount <= remaining else "OVER_BUDGET"
    audit(db, user, "SUBMIT", "EXPENSE", item.id, f"Remaining budget {remaining}")
    db.commit(); db.refresh(item)
    return item


@router.post("/expenses/{expense_id}/approve", response_model=ExpenseOut)
def approve_expense(expense_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.COST_APPROVE))):
    item = db.get(Expense, expense_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy chi phí")
    if item.status not in ["SUBMITTED", "OVER_BUDGET"]:
        raise HTTPException(409, "Đề nghị chi không chờ duyệt")
    if item.created_by == user.id:
        raise HTTPException(409, "Người tạo đề nghị không được tự duyệt")
    was_over_budget = item.status == "OVER_BUDGET"
    item.status = "APPROVED"; item.approved_by = user.id
    budget = db.scalar(select(Budget).where(Budget.id == item.budget_id).with_for_update())
    if not budget:
        raise HTTPException(422, "Đề nghị chưa gắn ngân sách hợp lệ")
    remaining = Decimal(budget.amount) - Decimal(budget.spent_amount) - Decimal(budget.committed_amount)
    if not was_over_budget and item.amount > remaining:
        raise HTTPException(409, "Ngân sách đã được sử dụng bởi giao dịch khác")
    criteria = [Budget.id == budget.id]
    if not was_over_budget:
        criteria.append(Budget.amount - Budget.spent_amount - Budget.committed_amount >= item.amount)
    changed = db.execute(update(Budget).where(*criteria).values(
        committed_amount=Budget.committed_amount + item.amount
    ))
    if changed.rowcount != 1:
        raise HTTPException(409, "Ngân sách vừa được giao dịch khác sử dụng")
    audit(db, user, "APPROVE", "EXPENSE", item.id, item.description); db.commit(); db.refresh(item)
    return item


@router.post("/expenses/{expense_id}/reject", response_model=ExpenseOut)
def reject_expense(expense_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.COST_APPROVE))):
    item = db.get(Expense, expense_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy chi phí")
    if item.status not in ["SUBMITTED", "OVER_BUDGET"]:
        raise HTTPException(409, "Chỉ từ chối đề nghị đang chờ duyệt")
    if item.created_by == user.id:
        raise HTTPException(409, "Người tạo đề nghị không được tự từ chối")
    item.status = "REJECTED"; item.approved_by = user.id
    audit(db, user, "REJECT", "EXPENSE", item.id, item.description); db.commit(); db.refresh(item)
    return item


@router.post("/expenses/{expense_id}/pay", response_model=ExpenseOut)
def pay_expense(expense_id: int, payload: ExpensePaymentIn, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.FINANCE_WRITE))):
    item = db.get(Expense, expense_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy đề nghị chi")
    if item.status != "APPROVED":
        raise HTTPException(409, "Chỉ thanh toán đề nghị chi đã duyệt")
    if item.approved_by == user.id:
        raise HTTPException(409, "Người duyệt không được đồng thời thanh toán")
    if payload.amount != item.amount:
        raise HTTPException(422, "Số thanh toán phải đúng bằng số tiền đã duyệt")
    payment = ExpensePayment(expense_id=item.id, paid_by=user.id, **payload.model_dump())
    budget = db.scalar(select(Budget).where(Budget.id == item.budget_id).with_for_update())
    if not budget:
        raise HTTPException(422, "Không tìm thấy ngân sách đã cam kết")
    if Decimal(budget.committed_amount) < payload.amount:
        raise HTTPException(409, "Số committed trên ngân sách không đủ")
    changed = db.execute(update(Budget).where(
        Budget.id == budget.id, Budget.committed_amount >= payload.amount,
    ).values(
        committed_amount=Budget.committed_amount - payload.amount,
        spent_amount=Budget.spent_amount + payload.amount,
    ))
    if changed.rowcount != 1:
        raise HTTPException(409, "Ngân sách vừa được cập nhật hoặc committed không đủ")
    add_project_actual_cost(db, item.project_id, payload.amount)
    item.status = "PAID"
    db.add(payment); audit(db, user, "PAY", "EXPENSE", item.id, f"{payload.method} {payload.transaction_ref or ''}")
    db.commit(); db.refresh(item)
    return item


@router.get("/budget-control")
def budget_control(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.COST_READ))):
    rows = db.scalars(select(Budget).order_by(Budget.department, Budget.period)).all()
    return [{
        "id": x.id, "code": x.code, "name": x.name, "department": x.department, "period": x.period,
        "approved_budget": x.amount, "committed": x.committed_amount, "actual": x.spent_amount,
        "remaining": Decimal(x.amount) - Decimal(x.committed_amount) - Decimal(x.spent_amount),
        "utilization_percent": ((Decimal(x.committed_amount) + Decimal(x.spent_amount)) / Decimal(x.amount) * 100) if x.amount else 0,
    } for x in rows]
