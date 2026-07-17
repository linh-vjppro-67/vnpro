from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models import SupportTicket, User
from app.schemas import SupportTicketCreate, SupportTicketOut
from app.services import audit

router = APIRouter(prefix="/support", tags=["Customer service"])


@router.get("/tickets", response_model=list[SupportTicketOut])
def tickets(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.SUPPORT_READ))):
    return db.scalars(select(SupportTicket).order_by(SupportTicket.created_at.desc())).all()


@router.post("/tickets", response_model=SupportTicketOut, status_code=201)
def create_ticket(payload: SupportTicketCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.SUPPORT_WRITE))):
    hours = {"CRITICAL": 2, "HIGH": 4, "MEDIUM": 24, "LOW": 48}.get(payload.priority.upper(), 24)
    item = SupportTicket(**payload.model_dump(), priority=payload.priority.upper(), assigned_to=user.id, sla_due_at=datetime.now(timezone.utc) + timedelta(hours=hours))
    db.add(item); db.flush(); audit(db, user, "CREATE", "SUPPORT_TICKET", item.id, item.subject); db.commit(); db.refresh(item)
    return item
