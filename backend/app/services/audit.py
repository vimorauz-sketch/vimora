from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session as DB

from app.core.db import utcnow
from app.models import AuditLog
from app.models.enums import ActorType


def audit(
    db: DB,
    action: str,
    *,
    actor_id: int | None = None,
    actor_type: str = ActorType.SYSTEM,
    entity_type: str | None = None,
    entity_id: Any = None,
    ip: str | None = None,
    user_agent: str | None = None,
    success: bool = True,
    data: dict | None = None,
) -> AuditLog:
    """Append an audit record within the caller's transaction (no secrets in `data`)."""
    entry = AuditLog(
        actor_id=actor_id,
        actor_type=str(actor_type),
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        ip_address=ip,
        user_agent=(user_agent or "")[:400] or None,
        success=success,
        data=data or {},
        created_at=utcnow(),
    )
    db.add(entry)
    return entry
