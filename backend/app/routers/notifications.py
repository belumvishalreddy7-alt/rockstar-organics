import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_user
from app.models.models import Notification, User

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("")
def list_my_notifications(user: User = Depends(require_user), db: Session = Depends(get_db)):
    items = db.query(Notification).filter(Notification.recipient_id == user.id).order_by(Notification.created_at.desc()).limit(100).all()
    return [{"id": n.id, "type": n.type, "title": n.title, "message": n.message, "is_read": n.is_read,
             "created_at": n.created_at.isoformat()} for n in items]


@router.post("/{notification_id}/read")
def mark_read(notification_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if not n or n.recipient_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found.")
    n.is_read = True
    n.read_at = dt.datetime.utcnow()
    db.commit()
    return {"ok": True}
