from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import AcceptanceRecord, ApprovalRequest, ApprovalRule, Contract, PurchaseRequest, Quotation, User
from app.services import audit

ENTITY_MODELS: dict[str, type] = {
    "QUOTATION": Quotation, "CONTRACT": Contract, "ACCEPTANCE_RECORD": AcceptanceRecord, "PURCHASE_REQUEST": PurchaseRequest,
}


def load_entity(db: Session, entity_type: str, entity_id: int):
    model = ENTITY_MODELS[entity_type]
    return db.get(model, entity_id)


def resolve_user_by_role(db: Session, role: str) -> User | None:
    return db.scalar(select(User).where(User.role == role, User.is_active == True).order_by(User.id))  # noqa: E712


def resolve_rule_role(
    db: Session, document_type: str, *, amount=None, discount=None, margin=None, over_budget=None,
) -> str | None:
    rules = db.scalars(select(ApprovalRule).where(
        ApprovalRule.document_type == document_type, ApprovalRule.is_active == True  # noqa: E712
    ).order_by(ApprovalRule.step_no)).all()
    for rule in rules:
        if rule.min_amount is not None and (amount is None or amount < rule.min_amount): continue
        if rule.max_amount is not None and (amount is None or amount > rule.max_amount): continue
        if rule.max_discount_percent is not None and (discount is None or discount <= rule.max_discount_percent): continue
        if rule.min_margin_percent is not None and (margin is None or margin >= rule.min_margin_percent): continue
        if rule.over_budget is not None and rule.over_budget != over_budget: continue
        return rule.approver_role
    return None


def request_approval(db: Session, *, entity_type: str, entity, requested_by: User, approver_id: int | None, reason: str | None, pending_status: str) -> ApprovalRequest:
    req = ApprovalRequest(entity_type=entity_type, entity_id=entity.id, requested_by=requested_by.id, approver_id=approver_id, status="PENDING", reason=reason)
    db.add(req)
    entity.status = pending_status
    audit(db, requested_by, "SUBMIT", entity_type, entity.id, reason)
    return req


def decide_approval(db: Session, *, approval: ApprovalRequest, entity, decided_by: User, approve: bool, note: str | None, approved_status: str, rejected_status: str) -> ApprovalRequest:
    if approval.status != "PENDING":
        raise ValueError("Yêu cầu này đã được xử lý")
    if approval.requested_by == decided_by.id:
        raise ValueError("Người gửi duyệt không được tự phê duyệt")
    approval.status = "APPROVED" if approve else "REJECTED"
    approval.decided_at = datetime.now(timezone.utc)
    approval.decision_note = note
    approval.approver_id = decided_by.id
    entity.status = approved_status if approve else rejected_status
    audit(db, decided_by, "APPROVE" if approve else "REJECT", approval.entity_type, entity.id, note)
    return approval
