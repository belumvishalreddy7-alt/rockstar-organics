"""Leadership profiles - see app.core.verifiable_workflow for the shared
draft -> submitted -> under_review -> verified/rejected -> approved ->
published -> archived transitions. Only a published profile is ever
returned publicly; nothing here is seeded with invented names."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.permissions import CONTENT_VERIFIERS, SETTINGS_MANAGERS
from app.core.verifiable_workflow import register_workflow_routes
from app.models.models import LeadershipProfile, User
from app.schemas.schemas import LeadershipProfileCreate, LeadershipProfileOut

router = APIRouter(prefix="/api/v1/leadership", tags=["leadership"])
register_workflow_routes(router, LeadershipProfile, entity_type="leadership_profile", label_field="full_name")


@router.get("/public", response_model=list[LeadershipProfileOut])
def list_public(db: Session = Depends(get_db)):
    return db.query(LeadershipProfile).filter(LeadershipProfile.status == "published") \
        .order_by(LeadershipProfile.sort_order, LeadershipProfile.full_name).all()


@router.get("/public/{item_id}", response_model=LeadershipProfileOut)
def get_public(item_id: str, db: Session = Depends(get_db)):
    item = db.get(LeadershipProfile, item_id)
    if not item or item.status != "published":
        raise HTTPException(status_code=404, detail="Leadership profile not found.")
    return item


@router.get("/admin", response_model=list[LeadershipProfileOut])
def list_admin(user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    return db.query(LeadershipProfile).order_by(LeadershipProfile.sort_order, LeadershipProfile.created_at.desc()).all()


@router.get("/admin/{item_id}", response_model=LeadershipProfileOut)
def get_admin(item_id: str, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    item = db.get(LeadershipProfile, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Leadership profile not found.")
    return item


@router.post("", response_model=LeadershipProfileOut)
def create(payload: LeadershipProfileCreate, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    item = LeadershipProfile(**payload.model_dump(), created_by_id=user.id, updated_by_id=user.id)
    db.add(item)
    db.flush()
    record_audit(db, actor_id=user.id, action="leadership_profile.create", entity_type="leadership_profile", entity_id=item.id,
                 summary=f"Leadership profile created: {item.full_name}")
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=LeadershipProfileOut)
def update(item_id: str, payload: LeadershipProfileCreate, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    item = db.get(LeadershipProfile, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Leadership profile not found.")
    if item.status == "published":
        raise HTTPException(status_code=400, detail="Unpublish before editing a published profile.")
    for field, value in payload.model_dump().items():
        setattr(item, field, value)
    item.updated_by_id = user.id
    if item.status in ("verified", "approved"):
        item.status = "draft"  # a change always re-enters the verification gate
    item.version += 1
    record_audit(db, actor_id=user.id, action="leadership_profile.update", entity_type="leadership_profile", entity_id=item.id,
                 summary=f"Leadership profile updated: {item.full_name}")
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}")
def delete(item_id: str, user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
    item = db.get(LeadershipProfile, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Leadership profile not found.")
    if item.status != "draft":
        raise HTTPException(status_code=400, detail="Only a draft record can be permanently deleted - archive it instead.")
    record_audit(db, actor_id=user.id, action="leadership_profile.delete", entity_type="leadership_profile", entity_id=item.id,
                 summary=f"Leadership profile deleted: {item.full_name}")
    db.delete(item)
    db.commit()
    return {"ok": True}
