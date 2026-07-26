from contextvars import ContextVar
import json
from sqlalchemy.orm import Session
from app.models import AuditLog, User

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
ip_ctx: ContextVar[str | None] = ContextVar("ip_address", default=None)


def audit(
    db: Session, user: User | None, action: str, entity: str,
    entity_id: str | int | None = None, details: str | None = None,
    old_values: dict | None = None, new_values: dict | None = None,
):
    db.add(AuditLog(
        user_id=user.id if user else None, action=action, entity=entity,
        entity_id=str(entity_id) if entity_id is not None else None, details=details,
        request_id=request_id_ctx.get(), ip_address=ip_ctx.get(),
        old_values=json.dumps(old_values, ensure_ascii=False, default=str) if old_values is not None else None,
        new_values=json.dumps(new_values, ensure_ascii=False, default=str) if new_values is not None else None,
    ))
