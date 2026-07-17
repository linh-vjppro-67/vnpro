from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.workflow import assert_transition
from app.db.session import get_db
from app.models import Task, User
from app.schemas import TaskCreate, TaskOut, TaskProgressNote, UserOut
from app.services import audit

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/assignees", response_model=list[UserOut])
def assignees(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    # any authenticated user can pick a colleague to assign a task to — task management is
    # company-wide, unlike /admin/users which is gated on USERS_MANAGE for org administration.
    return db.scalars(select(User).where(User.is_active == True).order_by(User.department, User.full_name)).all()  # noqa: E712


def _is_assignee(task: Task, user: User) -> bool:
    return task.assigned_to == user.id


def _is_assigner(task: Task, user: User) -> bool:
    return task.assigned_by == user.id or user.role in {"DIRECTOR", "SYSTEM_ADMIN"}


@router.get("", response_model=list[TaskOut])
def tasks(mine: bool = Query(default=False), status_: str | None = Query(default=None, alias="status"), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Task).order_by(Task.created_at.desc())
    if mine:
        stmt = stmt.where(or_(Task.assigned_to == user.id, Task.assigned_by == user.id))
    if status_:
        stmt = stmt.where(Task.status == status_)
    return db.scalars(stmt).all()


@router.post("", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if db.scalar(select(Task).where(Task.code == payload.code)):
        raise HTTPException(409, "Mã công việc đã tồn tại")
    if not db.get(User, payload.assigned_to):
        raise HTTPException(404, "Không tìm thấy người được giao việc")
    item = Task(**payload.model_dump(), status="NEW", assigned_by=user.id)
    db.add(item); db.flush(); audit(db, user, "CREATE", "TASK", item.id, item.title); db.commit(); db.refresh(item)
    return item


@router.post("/{task_id}/start", response_model=TaskOut)
def start_task(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(Task, task_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy công việc")
    if not _is_assignee(item, user):
        raise HTTPException(403, "Chỉ người được giao việc mới có thể bắt đầu công việc này")
    assert_transition("TASK", item.status, "IN_PROGRESS")
    item.status = "IN_PROGRESS"
    audit(db, user, "START", "TASK", item.id, item.title)
    db.commit(); db.refresh(item)
    return item


@router.post("/{task_id}/submit", response_model=TaskOut)
def submit_task(task_id: int, payload: TaskProgressNote, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(Task, task_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy công việc")
    if not _is_assignee(item, user):
        raise HTTPException(403, "Chỉ người được giao việc mới có thể xác nhận hoàn thành")
    assert_transition("TASK", item.status, "DONE_PENDING_REVIEW")
    item.status = "DONE_PENDING_REVIEW"
    item.progress_note = payload.note
    audit(db, user, "SUBMIT", "TASK", item.id, payload.note)
    db.commit(); db.refresh(item)
    return item


@router.post("/{task_id}/confirm", response_model=TaskOut)
def confirm_task(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(Task, task_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy công việc")
    if not _is_assigner(item, user):
        raise HTTPException(403, "Chỉ người giao việc mới có thể xác nhận kết quả")
    assert_transition("TASK", item.status, "CONFIRMED")
    item.status = "CONFIRMED"
    item.confirmed_by = user.id
    item.confirmed_at = datetime.now(timezone.utc)
    audit(db, user, "CONFIRM", "TASK", item.id, item.title)
    db.commit(); db.refresh(item)
    return item


@router.post("/{task_id}/reject", response_model=TaskOut)
def reject_task(task_id: int, payload: TaskProgressNote, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(Task, task_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy công việc")
    if not _is_assigner(item, user):
        raise HTTPException(403, "Chỉ người giao việc mới có thể yêu cầu làm lại")
    assert_transition("TASK", item.status, "IN_PROGRESS")
    item.status = "IN_PROGRESS"
    item.progress_note = payload.note
    audit(db, user, "REJECT", "TASK", item.id, payload.note)
    db.commit(); db.refresh(item)
    return item


@router.post("/{task_id}/cancel", response_model=TaskOut)
def cancel_task(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(Task, task_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy công việc")
    if not (_is_assignee(item, user) or _is_assigner(item, user)):
        raise HTTPException(403, "Bạn không có quyền hủy công việc này")
    assert_transition("TASK", item.status, "CANCELLED")
    item.status = "CANCELLED"
    audit(db, user, "CANCEL", "TASK", item.id, item.title)
    db.commit(); db.refresh(item)
    return item
