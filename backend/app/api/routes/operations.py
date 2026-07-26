from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.approvals import decide_approval, request_approval, resolve_user_by_role
from app.core.permissions import Permission
from app.core.workflow import DECISION_TARGETS, acceptance_needs_director_approval, assert_transition
from app.db.session import get_db
from app.models import AcceptanceRecord, ApprovalRequest, Project, SalesOrder, User, WorkOrder
from app.schemas import (
    AcceptanceRecordCreate, AcceptanceRecordOut, DecisionNote, ProjectOut, ProjectCreate,
    WorkOrderCreate, WorkOrderOut,
)
from app.services import audit

router = APIRouter(prefix="/operations", tags=["Operations"])


def _pending_approval(db: Session, entity_type: str, entity_id: int) -> ApprovalRequest | None:
    return db.scalar(select(ApprovalRequest).where(ApprovalRequest.entity_type == entity_type, ApprovalRequest.entity_id == entity_id, ApprovalRequest.status == "PENDING"))


def _decide(db: Session, entity_type: str, entity, user: User, approve: bool, note: str | None):
    approval = _pending_approval(db, entity_type, entity.id)
    if not approval:
        raise HTTPException(404, "Không có yêu cầu phê duyệt đang chờ xử lý")
    if approval.approver_id and approval.approver_id != user.id and user.role not in {"DIRECTOR", "SYSTEM_ADMIN"}:
        raise HTTPException(403, "Bạn không phải người được giao phê duyệt yêu cầu này")
    targets = DECISION_TARGETS[entity_type]
    try:
        decide_approval(db, approval=approval, entity=entity, decided_by=user, approve=approve, note=note, approved_status=targets["approved"], rejected_status=targets["rejected"])
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    db.commit(); db.refresh(entity)


@router.get("/projects", response_model=list[ProjectOut])
def projects(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.OPERATIONS_READ))):
    return db.scalars(select(Project).order_by(Project.due_date.asc())).all()


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.OPERATIONS_WRITE))):
    order = db.get(SalesOrder, payload.order_id)
    if not order:
        raise HTTPException(404, "Không tìm thấy đơn hàng")
    if order.status in {"DRAFT", "CANCELLED", "CLOSED"}:
        raise HTTPException(409, "Đơn hàng chưa sẵn sàng hoặc đã kết thúc")
    if db.scalar(select(Project).where(Project.order_id == order.id)):
        raise HTTPException(409, "Sales Order đã có Project")
    if db.scalar(select(Project).where(Project.code == payload.code)):
        raise HTTPException(409, "Mã Project đã tồn tại")
    project = Project(**payload.model_dump(), customer_id=order.customer_id)
    try:
        db.add(project); db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Sales Order đã có Project hoặc mã Project bị trùng")
    audit(db, user, "CREATE", "PROJECT", project.id, project.code); db.commit(); db.refresh(project)
    return project


# ---------------------------------------------------------------------------
# Work orders
# ---------------------------------------------------------------------------

@router.get("/work-orders", response_model=list[WorkOrderOut])
def work_orders(project_id: int | None = Query(default=None), db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.OPERATIONS_READ))):
    stmt = select(WorkOrder).order_by(WorkOrder.created_at.desc())
    if project_id:
        stmt = stmt.where(WorkOrder.project_id == project_id)
    return db.scalars(stmt).all()


@router.post("/work-orders", response_model=WorkOrderOut, status_code=201)
def create_work_order(payload: WorkOrderCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.OPERATIONS_WRITE))):
    if db.scalar(select(WorkOrder).where(WorkOrder.code == payload.code)):
        raise HTTPException(409, "Mã work order đã tồn tại")
    item = WorkOrder(**payload.model_dump(), status="PLANNED", created_by=user.id)
    db.add(item); db.flush(); audit(db, user, "CREATE", "WORK_ORDER", item.id, item.code); db.commit(); db.refresh(item)
    return item


@router.get("/work-orders/{work_order_id}", response_model=WorkOrderOut)
def get_work_order(work_order_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.OPERATIONS_READ))):
    item = db.get(WorkOrder, work_order_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy work order")
    return item


@router.post("/work-orders/{work_order_id}/start", response_model=WorkOrderOut)
def start_work_order(work_order_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.OPERATIONS_WRITE))):
    item = db.get(WorkOrder, work_order_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy work order")
    assert_transition("WORK_ORDER", item.status, "IN_PROGRESS")
    item.status = "IN_PROGRESS"
    audit(db, user, "START", "WORK_ORDER", item.id, item.code)
    db.commit(); db.refresh(item)
    return item


@router.post("/work-orders/{work_order_id}/complete", response_model=WorkOrderOut)
def complete_work_order(work_order_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.OPERATIONS_WRITE))):
    item = db.get(WorkOrder, work_order_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy work order")
    assert_transition("WORK_ORDER", item.status, "DONE")
    item.status = "DONE"
    audit(db, user, "COMPLETE", "WORK_ORDER", item.id, item.code)
    db.commit(); db.refresh(item)
    return item


# ---------------------------------------------------------------------------
# Acceptance records (biên bản nghiệm thu)
# ---------------------------------------------------------------------------

@router.get("/acceptance-records", response_model=list[AcceptanceRecordOut])
def acceptance_records(project_id: int | None = Query(default=None), db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.OPERATIONS_READ))):
    stmt = select(AcceptanceRecord).order_by(AcceptanceRecord.created_at.desc())
    if project_id:
        stmt = stmt.where(AcceptanceRecord.project_id == project_id)
    return db.scalars(stmt).all()


@router.post("/acceptance-records", response_model=AcceptanceRecordOut, status_code=201)
def create_acceptance_record(payload: AcceptanceRecordCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.OPERATIONS_WRITE))):
    work_order = db.get(WorkOrder, payload.work_order_id)
    if not work_order:
        raise HTTPException(404, "Không tìm thấy work order")
    if work_order.status != "DONE":
        raise HTTPException(409, "Chỉ lập biên bản nghiệm thu khi work order đã hoàn thành")
    if payload.acceptance_type not in {"PARTIAL", "FULL"}:
        raise HTTPException(422, "Loại nghiệm thu phải là PARTIAL hoặc FULL")
    if payload.acceptance_type == "FULL":
        unfinished = db.scalar(select(WorkOrder.id).where(
            WorkOrder.project_id == work_order.project_id, WorkOrder.status != "DONE"
        ).limit(1))
        if unfinished:
            raise HTTPException(409, "Nghiệm thu toàn bộ chỉ được lập khi mọi Work Order đã hoàn thành")
    if db.scalar(select(AcceptanceRecord).where(AcceptanceRecord.code == payload.code)):
        raise HTTPException(409, "Mã biên bản nghiệm thu đã tồn tại")
    item = AcceptanceRecord(**payload.model_dump(), project_id=work_order.project_id, status="DRAFT", created_by=user.id)
    db.add(item); db.flush(); audit(db, user, "CREATE", "ACCEPTANCE_RECORD", item.id, item.code); db.commit(); db.refresh(item)
    return item


@router.get("/acceptance-records/{record_id}", response_model=AcceptanceRecordOut)
def get_acceptance_record(record_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.OPERATIONS_READ))):
    item = db.get(AcceptanceRecord, record_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy biên bản nghiệm thu")
    return item


@router.post("/acceptance-records/{record_id}/submit", response_model=AcceptanceRecordOut)
def submit_acceptance_record(record_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.OPERATIONS_WRITE))):
    item = db.get(AcceptanceRecord, record_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy biên bản nghiệm thu")
    assert_transition("ACCEPTANCE_RECORD", item.status, "SUBMITTED")
    if not all([item.summary, item.customer_signed_by, item.signed_date, item.signed_file, item.checklist_result]):
        raise HTTPException(422, "Biên bản thiếu checklist hoặc hồ sơ ký")
    project = db.get(Project, item.project_id)
    needs_director = acceptance_needs_director_approval(project.budget_amount if project else 0)
    approver = resolve_user_by_role(db, "DIRECTOR" if needs_director else "TECH_SOLUTION")
    reason = "Dự án có ngân sách lớn" if needs_director else None
    request_approval(db, entity_type="ACCEPTANCE_RECORD", entity=item, requested_by=user, approver_id=approver.id if approver else None, reason=reason, pending_status="SUBMITTED")
    db.commit(); db.refresh(item)
    return item


@router.post("/acceptance-records/{record_id}/approve", response_model=AcceptanceRecordOut)
def approve_acceptance_record(record_id: int, payload: DecisionNote, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.OPERATIONS_APPROVE))):
    item = db.get(AcceptanceRecord, record_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy biên bản nghiệm thu")
    _decide(db, "ACCEPTANCE_RECORD", item, user, True, payload.note)
    return item


@router.post("/acceptance-records/{record_id}/reject", response_model=AcceptanceRecordOut)
def reject_acceptance_record(record_id: int, payload: DecisionNote, db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.OPERATIONS_APPROVE))):
    item = db.get(AcceptanceRecord, record_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy biên bản nghiệm thu")
    _decide(db, "ACCEPTANCE_RECORD", item, user, False, payload.note)
    return item
