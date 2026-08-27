import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.permissions import PRODUCT_MANAGERS
from app.models.models import Announcement, User
from app.schemas.schemas import AnnouncementCreate

router = APIRouter(prefix="/api/v1/announcements", tags=["announcements"])

VALID_TRANSITIONS = {"draft": {"in_review", "archived"}, "in_review": {"published", "draft"},
                      "published": {"archived"}, "archived": {"draft"}}


def _serialize(a: Announcement) -> dict:
    return {"id": a.id, "title": a.title, "slug": a.slug, "summary": a.summary, "body": a.body,
            "announcement_type": a.announcement_type, "status": a.status, "featured": a.featured,
            "publish_date": a.publish_date.isoformat() if a.publish_date else None,
            "expiry_date": a.expiry_date.isoformat() if a.expiry_date else None}


@router.get("/public")
def public_announcements(db: Session = Depends(get_db)):
    now = dt.datetime.utcnow()
    items = (
        db.query(Announcement)
        .filter(Announcement.status == "published")
        .filter((Announcement.expiry_date.is_(None)) | (Announcement.expiry_date > now))
        .order_by(Announcement.publish_date.desc())
        .all()
    )
    return [_serialize(a) for a in items]


@router.get("/public/{slug}")
def public_announcement_detail(slug: str, db: Session = Depends(get_db)):
    a = db.query(Announcement).filter(Announcement.slug == slug, Announcement.status == "published").first()
    if not a:
        raise HTTPException(status_code=404, detail="Announcement not found.")
    return _serialize(a)


@router.get("")
def list_announcements(status: str | None = None, user: User = Depends(require_roles(*PRODUCT_MANAGERS, "super_admin")),
                        db: Session = Depends(get_db)):
    query = db.query(Announcement)
    if status:
        query = query.filter(Announcement.status == status)
    return [_serialize(a) for a in query.order_by(Announcement.updated_at.desc()).all()]


@router.post("")
def create_announcement(payload: AnnouncementCreate, user: User = Depends(require_roles(*PRODUCT_MANAGERS, "super_admin")),
                         db: Session = Depends(get_db)):
    if db.query(Announcement).filter(Announcement.slug == payload.slug).first():
        raise HTTPException(status_code=400, detail="An announcement with this slug already exists.")
    a = Announcement(**payload.model_dump(), status="draft", created_by_id=user.id)
    db.add(a)
    db.flush()
    record_audit(db, actor_id=user.id, action="announcement.create", entity_type="announcement", entity_id=a.id,
                 summary=f"Created draft announcement {a.title}")
    db.commit()
    db.refresh(a)
    return _serialize(a)


@router.post("/{announcement_id}/transition/{new_status}")
def transition_announcement(announcement_id: str, new_status: str,
                             user: User = Depends(require_roles(*PRODUCT_MANAGERS, "super_admin")), db: Session = Depends(get_db)):
    a = db.get(Announcement, announcement_id)
    if not a:
        raise HTTPException(status_code=404, detail="Announcement not found.")
    allowed = VALID_TRANSITIONS.get(a.status, set())
    if new_status not in allowed:
        raise HTTPException(status_code=400, detail=f"Cannot move announcement from '{a.status}' to '{new_status}'.")
    if new_status == "published":
        a.publish_date = dt.datetime.utcnow()
    old = a.status
    a.status = new_status
    record_audit(db, actor_id=user.id, action=f"announcement.{new_status}", entity_type="announcement", entity_id=a.id,
                 summary=f"Announcement {a.title} moved from {old} to {new_status}")
    db.commit()
    db.refresh(a)
    return _serialize(a)
