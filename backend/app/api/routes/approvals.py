from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.approvals import decide_approval, load_entity
from app.core.workflow import DECISION_TARGETS
from app.db.session import get_db
from app.models import ApprovalRequest, User
from app.schemas import ApprovalDecision, ApprovalRequestOut

router = APIRouter(prefix="/approvals", tags=["Approvals"])


# This inbox spans every module (sales quotations/contracts, technical acceptance records, and
# future purchasing/cost requests), so it is gated on being logged in rather than on any one
# module's permission — the real authorization for deciding is the approver_id/role check below,
# same as the contextual wrapper endpoints (crm.py, operations.py) already enforce.
@router.get("", response_model=list[ApprovalRequestOut])
def list_approvals(mine: bool = Query(default=False), status_: str | None = Query(default=None, alias="status"), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc())
    if mine:
        stmt = stmt.where(ApprovalRequest.approver_id == user.id)
    if status_:
        stmt = stmt.where(ApprovalRequest.status == status_)
    return db.scalars(stmt).all()


@router.post("/{approval_id}/decide", response_model=ApprovalRequestOut)
def decide(approval_id: int, payload: ApprovalDecision, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    approval = db.get(ApprovalRequest, approval_id)
    if not approval:
        raise HTTPException(404, "Không tìm thấy yêu cầu phê duyệt")
    if approval.approver_id and approval.approver_id != user.id and user.role not in {"DIRECTOR", "SYSTEM_ADMIN"}:
        raise HTTPException(403, "Bạn không phải người được giao phê duyệt yêu cầu này")
    entity = load_entity(db, approval.entity_type, approval.entity_id)
    if not entity:
        raise HTTPException(404, "Không tìm thấy chứng từ liên quan")
    targets = DECISION_TARGETS[approval.entity_type]
    try:
        decide_approval(db, approval=approval, entity=entity, decided_by=user, approve=payload.approve, note=payload.note, approved_status=targets["approved"], rejected_status=targets["rejected"])
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    db.commit(); db.refresh(approval)
    return approval
