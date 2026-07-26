from datetime import date, timedelta
from calendar import monthrange
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models import Budget, Expense, Opportunity, Product, Project, Receivable, SalesInvoice, SupportTicket, User
from app.schemas import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def money(value):
    return Decimal(value or 0)


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.DASHBOARD_READ))):
    revenue = money(db.scalar(select(func.sum(SalesInvoice.total_amount)).where(SalesInvoice.status == "ISSUED")))
    cost = money(db.scalar(select(func.sum(Project.actual_cost)).where(Project.status != "CANCELLED")))
    pipeline = money(db.scalar(select(func.sum(Opportunity.expected_value * Opportunity.probability / 100)).where(Opportunity.stage.notin_(["WON", "LOST"]))))
    open_recv = money(db.scalar(select(func.sum(Receivable.amount - Receivable.paid_amount)).where(Receivable.status != "PAID")))
    overdue = money(db.scalar(select(func.sum(Receivable.amount - Receivable.paid_amount)).where(Receivable.status != "PAID", Receivable.due_date < date.today())))
    budget = money(db.scalar(select(func.sum(Budget.amount)).where(Budget.status == "APPROVED")))
    spent = money(db.scalar(select(func.sum(Expense.amount)).where(Expense.status == "PAID")))
    active_projects = db.scalar(select(func.count(Project.id)).where(Project.status.in_(["PLANNING", "IN_PROGRESS", "WAITING_ACCEPTANCE"]))) or 0
    open_tickets = db.scalar(select(func.count(SupportTicket.id)).where(SupportTicket.status.notin_(["RESOLVED", "CLOSED"]))) or 0
    low_stock = db.scalar(select(func.count(Product.id)).where(Product.quantity_on_hand <= Product.min_stock)) or 0

    monthly = []
    cursor = date.today().replace(day=1)
    months = []
    for _ in range(6):
        months.append(cursor)
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    for month in reversed(months):
        end = month.replace(day=monthrange(month.year, month.month)[1])
        value = money(db.scalar(select(func.sum(SalesInvoice.total_amount)).where(
            SalesInvoice.status == "ISSUED", SalesInvoice.invoice_date >= month, SalesInvoice.invoice_date <= end,
        )))
        monthly.append({"month": f"T{month.month}/{str(month.year)[2:]}", "value": float(value)})
    stages = db.execute(select(Opportunity.stage, func.count(Opportunity.id), func.sum(Opportunity.expected_value)).group_by(Opportunity.stage)).all()
    funnel = [{"stage": row[0], "count": row[1], "value": float(row[2] or 0)} for row in stages]
    cats = db.execute(select(Expense.category, func.sum(Expense.amount)).where(Expense.status == "PAID").group_by(Expense.category)).all()
    expense_categories = [{"category": row[0], "value": float(row[1] or 0)} for row in cats]
    alerts = []
    if overdue > 0:
        alerts.append({"level": "danger", "title": "Công nợ quá hạn", "message": f"Tổng giá trị quá hạn {overdue:,.0f} đ"})
    if low_stock:
        alerts.append({"level": "warning", "title": "Tồn kho dưới định mức", "message": f"Có {low_stock} sản phẩm cần bổ sung"})
    if open_tickets:
        alerts.append({"level": "info", "title": "Yêu cầu CSKH đang mở", "message": f"Có {open_tickets} yêu cầu cần theo dõi"})

    return DashboardSummary(
        revenue=revenue, gross_profit=revenue-cost, pipeline_value=pipeline,
        open_receivables=open_recv, overdue_receivables=overdue,
        approved_budget=budget, spent_budget=spent, active_projects=active_projects,
        open_tickets=open_tickets, low_stock_products=low_stock,
        monthly_revenue=monthly, sales_funnel=funnel, expense_by_category=expense_categories, alerts=alerts,
    )
