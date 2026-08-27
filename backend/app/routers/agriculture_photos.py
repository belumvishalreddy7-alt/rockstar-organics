"""
Agriculture photo gallery.

Upload -> Metadata -> Usage Permission -> Review -> Approve -> Publish.
Only photographs Rockstar Organics owns or has a verified usage licence for
may be published; the public list only ever returns status == "published"
records, and every field the spec calls out as "never invent" (location,
crop, date, photographer/source) stays nullable, rendered as "Information
pending verification." by the frontend when unset rather than fabricated
here.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.permissions import CONTENT_VERIFIERS
from app.models.models import AgriculturePhoto, User
from app.schemas.schemas import AgriculturePhotoCreate

router = APIRouter(prefix="/api/v1/media/agriculture", tags=["agriculture-photos"])

VALID_STATUSES = {"draft", "under_review", "approved", "published", "archived"}


def _public_shape(p: AgriculturePhoto) -> dict:
    return {
        "id": p.id, "title": p.title, "caption": p.caption, "description": p.description,
        "category": p.category,
        "location": p.location or "Information pending verification.",
        "crop": p.crop or "Information pending verification.",
        "photo_date": p.photo_date.isoformat() if p.photo_date else "Information pending verification.",
        "photographer_source": p.photographer_source or "Information pending verification.",
        "alt_text": p.alt_text,
        "image_url": f"/api/v1/media/gallery/{p.id}",
    }


def _admin_shape(p: AgriculturePhoto) -> dict:
    base = _public_shape(p)
    base.update({
        "status": p.status, "usage_rights_verified": p.usage_rights_verified,
        "usage_rights_notes": p.usage_rights_notes, "uploaded_by_id": p.uploaded_by_id,
        "created_at": p.created_at.isoformat(), "updated_at": p.updated_at.isoformat(),
    })
    return base


@router.get("")
def list_public_photos(category: str | None = None, db: Session = Depends(get_db)):
    query = db.query(AgriculturePhoto).filter(AgriculturePhoto.status == "published")
    if category:
        query = query.filter(AgriculturePhoto.category == category)
    return [_public_shape(p) for p in query.order_by(AgriculturePhoto.created_at.desc()).all()]


@router.get("/admin")
def list_all_photos(user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    items = db.query(AgriculturePhoto).order_by(AgriculturePhoto.created_at.desc()).all()
    return [_admin_shape(p) for p in items]


@router.post("")
def create_photo(payload: AgriculturePhotoCreate, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    if not payload.usage_rights_verified:
        # Not a hard block - a photo can be uploaded pending a rights check -
        # but it can never be approved/published until verified (enforced below).
        pass
    photo = AgriculturePhoto(**payload.model_dump(), uploaded_by_id=user.id, status="draft")
    db.add(photo)
    db.flush()
    record_audit(db, actor_id=user.id, action="agriculture_photo.create", entity_type="agriculture_photo", entity_id=photo.id,
                 summary=f"Agriculture photo uploaded: {photo.title}")
    db.commit()
    db.refresh(photo)
    return _admin_shape(photo)


@router.post("/{photo_id}/status/{status}")
def change_status(photo_id: str, status: str, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status.")
    photo = db.get(AgriculturePhoto, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found.")
    if status in ("approved", "published") and not photo.usage_rights_verified:
        raise HTTPException(status_code=400, detail="Usage rights must be verified before this photo can be approved or published.")
    photo.status = status
    photo.reviewed_by_id = user.id
    record_audit(db, actor_id=user.id, action="agriculture_photo.status_change", entity_type="agriculture_photo", entity_id=photo.id,
                 summary=f"Photo {photo.title} -> {status}")
    db.commit()
    return _admin_shape(photo)
