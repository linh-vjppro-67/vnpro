from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import AcceptanceRecord, ApprovalRequest, Contract, PurchaseRequest, Quotation, User
from app.services import audit

ENTITY_MODELS: dict[str, type] = {
    "QUOTATION": Quotation, "CONTRACT": Contract, "ACCEPTANCE_RECORD": AcceptanceRecord, "PURCHASE_REQUEST": PurchaseRequest,
}


def load_entity(db: Session, entity_type: str, entity_id: int):
    model = ENTITY_MODELS[entity_type]
    return db.get(model, entity_id)


def resolve_user_by_role(db: Session, role: str) -> User | None:
    return db.scalar(select(User).where(User.role == role, User.is_active == True).order_by(User.id))  # noqa: E712


def request_approval(db: Session, *, entity_type: str, entity, requested_by: User, approver_id: int | None, reason: str | None, pending_status: str) -> ApprovalRequest:
    req = ApprovalRequest(entity_type=entity_type, entity_id=entity.id, requested_by=requested_by.id, approver_id=approver_id, status="PENDING", reason=reason)
    db.add(req)
    entity.status = pending_status
    audit(db, requested_by, "SUBMIT", entity_type, entity.id, reason)
    return req


def decide_approval(db: Session, *, approval: ApprovalRequest, entity, decided_by: User, approve: bool, note: str | None, approved_status: str, rejected_status: str) -> ApprovalRequest:
    if approval.status != "PENDING":
        raise ValueError("Yêu cầu này đã được xử lý")
    approval.status = "APPROVED" if approve else "REJECTED"
    approval.decided_at = datetime.now(timezone.utc)
    approval.decision_note = note
    approval.approver_id = decided_by.id
    entity.status = approved_status if approve else rejected_status
    audit(db, decided_by, "APPROVE" if approve else "REJECT", approval.entity_type, entity.id, note)
    return approval
