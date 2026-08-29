"""Quality & Safety certifications. See app.core.verifiable_workflow for
the shared status transitions. The public list only ever returns
published certifications; nothing here is seeded with invented
certificates."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.permissions import CONTENT_VERIFIERS, SETTINGS_MANAGERS
from app.core.verifiable_workflow import register_workflow_routes
from app.models.models import Certification, User
from app.schemas.schemas import CertificationCreate, CertificationOut

router = APIRouter(prefix="/api/v1/certifications", tags=["certifications"])
register_workflow_routes(router, Certification, entity_type="certification", label_field="name")


@router.get("/public", response_model=list[CertificationOut])
def list_public(db: Session = Depends(get_db)):
    return db.query(Certification).filter(Certification.status == "published").order_by(Certification.name).all()


@router.get("/admin", response_model=list[CertificationOut])
def list_admin(user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    return db.query(Certification).order_by(Certification.created_at.desc()).all()


@router.post("", response_model=CertificationOut)
def create(payload: CertificationCreate, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    item = Certification(**payload.model_dump(), created_by_id=user.id, updated_by_id=user.id)
    db.add(item)
    db.flush()
    record_audit(db, actor_id=user.id, action="certification.create", entity_type="certification", entity_id=item.id,
                 summary=f"Certification created: {item.name}")
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=CertificationOut)
def update(item_id: str, payload: CertificationCreate, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    item = db.get(Certification, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Certification not found.")
    if item.status == "published":
        raise HTTPException(status_code=400, detail="Unpublish before editing a published certification.")
    for field, value in payload.model_dump().items():
        setattr(item, field, value)
    item.updated_by_id = user.id
    if item.status in ("verified", "approved"):
        item.status = "draft"
    item.version += 1
    record_audit(db, actor_id=user.id, action="certification.update", entity_type="certification", entity_id=item.id,
                 summary=f"Certification updated: {item.name}")
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}")
def delete(item_id: str, user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
    item = db.get(Certification, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Certification not found.")
    if item.status != "draft":
        raise HTTPException(status_code=400, detail="Only a draft record can be permanently deleted - archive it instead.")
    record_audit(db, actor_id=user.id, action="certification.delete", entity_type="certification", entity_id=item.id,
                 summary=f"Certification deleted: {item.name}")
    db.delete(item)
    db.commit()
    return {"ok": True}
