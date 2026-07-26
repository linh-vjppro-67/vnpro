from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models import Project, SalesOrder, SalesOrderItem, SupportTicket, TicketEvent, User, WarrantyProfile
from app.schemas import SupportTicketCreate, SupportTicketOut
from app.services import audit

router = APIRouter(prefix="/support", tags=["Customer service"])


class TicketAction(BaseModel):
    note: str
    assignee_id: int | None = None


@router.get("/tickets", response_model=list[SupportTicketOut])
def tickets(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.SUPPORT_READ))):
    return db.scalars(select(SupportTicket).order_by(SupportTicket.created_at.desc())).all()


@router.post("/tickets", response_model=SupportTicketOut, status_code=201)
def create_ticket(payload: SupportTicketCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SUPPORT_WRITE))):
    hours = {"CRITICAL": 2, "HIGH": 4, "MEDIUM": 24, "LOW": 48}.get(payload.priority.upper(), 24)
    warranty_status = "NOT_CHECKED"
    if payload.sales_order_id:
        order = db.get(SalesOrder, payload.sales_order_id)
        if not order or order.customer_id != payload.customer_id:
            raise HTTPException(422, "Đơn hàng không thuộc khách hàng của ticket")
        if payload.product_id and not db.scalar(select(SalesOrderItem.id).where(
            SalesOrderItem.sales_order_id == order.id, SalesOrderItem.product_id == payload.product_id
        )):
            raise HTTPException(422, "Sản phẩm không thuộc đơn hàng")
        warranty = db.scalar(select(WarrantyProfile).where(
            WarrantyProfile.sales_order_id == payload.sales_order_id,
            WarrantyProfile.status == "ACTIVE",
            WarrantyProfile.start_date <= datetime.now(timezone.utc).date(),
            WarrantyProfile.end_date >= datetime.now(timezone.utc).date(),
        ))
        warranty_status = "IN_WARRANTY" if warranty else "OUT_OF_WARRANTY"
    if payload.project_id:
        project = db.get(Project, payload.project_id)
        if not project or project.customer_id != payload.customer_id or (
            payload.sales_order_id and project.order_id != payload.sales_order_id
        ):
            raise HTTPException(422, "Project không thuộc khách hàng/đơn hàng của ticket")
    values = payload.model_dump()
    values["priority"] = payload.priority.upper()
    item = SupportTicket(**values, assigned_to=user.id,
                         warranty_status=warranty_status, sla_due_at=datetime.now(timezone.utc) + timedelta(hours=hours))
    db.add(item); db.flush(); audit(db, user, "CREATE", "SUPPORT_TICKET", item.id, item.subject); db.commit(); db.refresh(item)
    return item


@router.get("/tickets/{ticket_id}/events")
def ticket_events(ticket_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.SUPPORT_READ))):
    return db.scalars(select(TicketEvent).where(TicketEvent.ticket_id == ticket_id).order_by(TicketEvent.created_at.desc())).all()


@router.post("/tickets/{ticket_id}/assign", response_model=SupportTicketOut)
def assign_ticket(ticket_id: int, payload: TicketAction, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SUPPORT_WRITE))):
    item = db.get(SupportTicket, ticket_id)
    if not item or not payload.assignee_id or not db.get(User, payload.assignee_id):
        raise HTTPException(422, "Ticket hoặc người phụ trách không hợp lệ")
    if item.status in ["CLOSED", "CANCELLED"]:
        raise HTTPException(409, "Ticket đã đóng")
    item.assigned_to = payload.assignee_id; item.status = "ASSIGNED"
    db.add(TicketEvent(ticket_id=item.id, action="ASSIGN", note=payload.note, actor_id=user.id))
    audit(db, user, "ASSIGN", "SUPPORT_TICKET", item.id, payload.note); db.commit(); db.refresh(item)
    return item


@router.post("/tickets/{ticket_id}/respond", response_model=SupportTicketOut)
def respond_ticket(ticket_id: int, payload: TicketAction, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SUPPORT_WRITE))):
    item = db.get(SupportTicket, ticket_id)
    if not item or item.status in ["CLOSED", "CANCELLED"]:
        raise HTTPException(409, "Ticket không thể phản hồi")
    if item.assigned_to and item.assigned_to != user.id and user.role not in {"DIRECTOR", "SYSTEM_ADMIN", "CUSTOMER_SERVICE"}:
        raise HTTPException(403, "Ticket được giao cho người xử lý khác")
    if not item.first_response_at:
        item.first_response_at = datetime.now(timezone.utc)
    item.status = "IN_PROGRESS"
    db.add(TicketEvent(ticket_id=item.id, action="RESPOND", note=payload.note, actor_id=user.id))
    audit(db, user, "RESPOND", "SUPPORT_TICKET", item.id, payload.note); db.commit(); db.refresh(item)
    return item


@router.post("/tickets/{ticket_id}/resolve", response_model=SupportTicketOut)
def resolve_ticket(ticket_id: int, payload: TicketAction, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SUPPORT_WRITE))):
    item = db.get(SupportTicket, ticket_id)
    if not item or item.status not in ["OPEN", "ASSIGNED", "IN_PROGRESS"]:
        raise HTTPException(409, "Ticket không thể resolve")
    if item.assigned_to and item.assigned_to != user.id and user.role not in {"DIRECTOR", "SYSTEM_ADMIN", "CUSTOMER_SERVICE"}:
        raise HTTPException(403, "Ticket được giao cho người xử lý khác")
    item.status = "RESOLVED"; item.resolution = payload.note; item.resolved_at = datetime.now(timezone.utc)
    db.add(TicketEvent(ticket_id=item.id, action="RESOLVE", note=payload.note, actor_id=user.id))
    audit(db, user, "RESOLVE", "SUPPORT_TICKET", item.id, payload.note); db.commit(); db.refresh(item)
    return item


@router.post("/tickets/{ticket_id}/close", response_model=SupportTicketOut)
def close_ticket(ticket_id: int, payload: TicketAction, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SUPPORT_WRITE))):
    item = db.get(SupportTicket, ticket_id)
    if not item or item.status != "RESOLVED" or not item.resolution:
        raise HTTPException(409, "Chỉ đóng ticket đã xử lý và có kết quả")
    item.status = "CLOSED"
    db.add(TicketEvent(ticket_id=item.id, action="CLOSE", note=payload.note, actor_id=user.id))
    audit(db, user, "CLOSE", "SUPPORT_TICKET", item.id, payload.note); db.commit(); db.refresh(item)
    return item


@router.post("/tickets/{ticket_id}/reopen", response_model=SupportTicketOut)
def reopen_ticket(ticket_id: int, payload: TicketAction, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SUPPORT_WRITE))):
    item = db.get(SupportTicket, ticket_id)
    if not item or item.status != "CLOSED":
        raise HTTPException(409, "Chỉ mở lại ticket đã đóng")
    item.status = "IN_PROGRESS"
    db.add(TicketEvent(ticket_id=item.id, action="REOPEN", note=payload.note, actor_id=user.id))
    audit(db, user, "REOPEN", "SUPPORT_TICKET", item.id, payload.note); db.commit(); db.refresh(item)
    return item
