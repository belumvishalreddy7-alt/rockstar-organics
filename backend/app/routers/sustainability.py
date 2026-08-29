"""Sustainability initiatives. See app.core.verifiable_workflow for the
shared status transitions. `measurable_results` is free text and is only
ever filled in with a real, sourced figure - never a placeholder statistic
invented to make the page look populated."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.permissions import CONTENT_VERIFIERS, SETTINGS_MANAGERS
from app.core.verifiable_workflow import register_workflow_routes
from app.models.models import SustainabilityInitiative, User
from app.schemas.schemas import SustainabilityInitiativeCreate, SustainabilityInitiativeOut

router = APIRouter(prefix="/api/v1/sustainability/initiatives", tags=["sustainability"])
register_workflow_routes(router, SustainabilityInitiative, entity_type="sustainability_initiative", label_field="title")


@router.get("/public", response_model=list[SustainabilityInitiativeOut])
def list_public(db: Session = Depends(get_db)):
    return db.query(SustainabilityInitiative).filter(SustainabilityInitiative.status == "published") \
        .order_by(SustainabilityInitiative.start_date.desc()).all()


@router.get("/admin", response_model=list[SustainabilityInitiativeOut])
def list_admin(user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    return db.query(SustainabilityInitiative).order_by(SustainabilityInitiative.created_at.desc()).all()


@router.post("", response_model=SustainabilityInitiativeOut)
def create(payload: SustainabilityInitiativeCreate, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    item = SustainabilityInitiative(**payload.model_dump(), created_by_id=user.id, updated_by_id=user.id)
    db.add(item)
    db.flush()
    record_audit(db, actor_id=user.id, action="sustainability_initiative.create", entity_type="sustainability_initiative", entity_id=item.id,
                 summary=f"Sustainability initiative created: {item.title}")
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=SustainabilityInitiativeOut)
def update(item_id: str, payload: SustainabilityInitiativeCreate, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    item = db.get(SustainabilityInitiative, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Sustainability initiative not found.")
    if item.status == "published":
        raise HTTPException(status_code=400, detail="Unpublish before editing a published initiative.")
    for field, value in payload.model_dump().items():
        setattr(item, field, value)
    item.updated_by_id = user.id
    if item.status in ("verified", "approved"):
        item.status = "draft"
    item.version += 1
    record_audit(db, actor_id=user.id, action="sustainability_initiative.update", entity_type="sustainability_initiative", entity_id=item.id,
                 summary=f"Sustainability initiative updated: {item.title}")
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}")
def delete(item_id: str, user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
    item = db.get(SustainabilityInitiative, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Sustainability initiative not found.")
    if item.status != "draft":
        raise HTTPException(status_code=400, detail="Only a draft record can be permanently deleted - archive it instead.")
    record_audit(db, actor_id=user.id, action="sustainability_initiative.delete", entity_type="sustainability_initiative", entity_id=item.id,
                 summary=f"Sustainability initiative deleted: {item.title}")
    db.delete(item)
    db.commit()
    return {"ok": True}
