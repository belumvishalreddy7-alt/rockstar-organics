"""Helper for writing audit log entries. Never pass secrets or full
documents into `summary` or `metadata`."""
from sqlalchemy.orm import Session

from app.models.models import AuditLog


def record_audit(
    db: Session,
    *,
    actor_id: str | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    summary: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary[:500],
            ip_address=ip_address,
            user_agent=(user_agent or "")[:255],
        )
    )
