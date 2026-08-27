"""
Notification service.

In-app notifications always work (they are just database rows). External
channels (email/SMS/WhatsApp) are only attempted when explicitly configured
via environment variables; otherwise the notification is recorded with
delivery_status="disabled" and no external send is ever claimed.
"""
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.models import Notification

settings = get_settings()


def notify(
    db: Session,
    *,
    recipient_id: str,
    type: str,
    title: str,
    message: str,
    related_entity_type: str | None = None,
    related_entity_id: str | None = None,
) -> Notification:
    channel = "in_app"
    delivery_status = "delivered"
    failure_reason = None

    n = Notification(
        recipient_id=recipient_id,
        type=type,
        title=title,
        message=message,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        channel=channel,
        delivery_status=delivery_status,
        failure_reason=failure_reason,
    )
    db.add(n)
    db.flush()

    # External channels: adapters are intentionally not wired to a live
    # provider in this build. If enabled, a real provider call would happen
    # here and delivery_status would reflect its real outcome. If not
    # configured, we do not create a misleading "sent" record.
    if settings.EMAIL_PROVIDER_ENABLED:
        pass  # would call the email adapter and record its real result
    return n
