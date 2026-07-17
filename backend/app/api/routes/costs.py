from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models import Budget, Expense, User
from app.schemas import BudgetOut, ExpenseCreate, ExpenseOut
from app.services import audit

router = APIRouter(prefix="/costs", tags=["Cost management"])


@router.get("/budgets", response_model=list[BudgetOut])
def budgets(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.COST_READ))):
    return db.scalars(select(Budget).order_by(Budget.department, Budget.period)).all()


@router.get("/expenses", response_model=list[ExpenseOut])
def expenses(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.COST_READ))):
    return db.scalars(select(Expense).order_by(Expense.expense_date.desc(), Expense.created_at.desc())).all()


@router.post("/expenses", response_model=ExpenseOut, status_code=201)
def create_expense(payload: ExpenseCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.COST_WRITE))):
    item = Expense(**payload.model_dump(), created_by=user.id, status="PENDING")
    db.add(item); db.flush(); audit(db, user, "CREATE", "EXPENSE", item.id, item.description); db.commit(); db.refresh(item)
    return item


@router.post("/expenses/{expense_id}/approve", response_model=ExpenseOut)
def approve_expense(expense_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.COST_APPROVE))):
    item = db.get(Expense, expense_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy chi phí")
    item.status = "APPROVED"; item.approved_by = user.id
    audit(db, user, "APPROVE", "EXPENSE", item.id, item.description); db.commit(); db.refresh(item)
    return item


@router.post("/expenses/{expense_id}/reject", response_model=ExpenseOut)
def reject_expense(expense_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.COST_APPROVE))):
    item = db.get(Expense, expense_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy chi phí")
    item.status = "REJECTED"; item.approved_by = user.id
    audit(db, user, "REJECT", "EXPENSE", item.id, item.description); db.commit(); db.refresh(item)
    return item
