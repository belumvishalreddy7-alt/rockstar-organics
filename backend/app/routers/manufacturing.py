"""Manufacturing facilities - see app.core.verifiable_workflow for the
shared status transitions. Only a published facility is ever returned
publicly; nothing here is seeded with invented locations."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.permissions import CONTENT_VERIFIERS, SETTINGS_MANAGERS
from app.core.verifiable_workflow import register_workflow_routes
from app.models.models import ManufacturingFacility, User
from app.schemas.schemas import ManufacturingFacilityCreate, ManufacturingFacilityOut

router = APIRouter(prefix="/api/v1/manufacturing/facilities", tags=["manufacturing"])
register_workflow_routes(router, ManufacturingFacility, entity_type="manufacturing_facility", label_field="name")


@router.get("/public", response_model=list[ManufacturingFacilityOut])
def list_public(db: Session = Depends(get_db)):
    return db.query(ManufacturingFacility).filter(ManufacturingFacility.status == "published") \
        .order_by(ManufacturingFacility.name).all()


@router.get("/public/{item_id}", response_model=ManufacturingFacilityOut)
def get_public(item_id: str, db: Session = Depends(get_db)):
    item = db.get(ManufacturingFacility, item_id)
    if not item or item.status != "published":
        raise HTTPException(status_code=404, detail="Manufacturing facility not found.")
    return item


@router.get("/admin", response_model=list[ManufacturingFacilityOut])
def list_admin(user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    return db.query(ManufacturingFacility).order_by(ManufacturingFacility.created_at.desc()).all()


@router.get("/admin/{item_id}", response_model=ManufacturingFacilityOut)
def get_admin(item_id: str, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    item = db.get(ManufacturingFacility, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Manufacturing facility not found.")
    return item


@router.post("", response_model=ManufacturingFacilityOut)
def create(payload: ManufacturingFacilityCreate, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    item = ManufacturingFacility(**payload.model_dump(), created_by_id=user.id, updated_by_id=user.id)
    db.add(item)
    db.flush()
    record_audit(db, actor_id=user.id, action="manufacturing_facility.create", entity_type="manufacturing_facility", entity_id=item.id,
                 summary=f"Manufacturing facility created: {item.name}")
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=ManufacturingFacilityOut)
def update(item_id: str, payload: ManufacturingFacilityCreate, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    item = db.get(ManufacturingFacility, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Manufacturing facility not found.")
    if item.status == "published":
        raise HTTPException(status_code=400, detail="Unpublish before editing a published facility.")
    for field, value in payload.model_dump().items():
        setattr(item, field, value)
    item.updated_by_id = user.id
    if item.status in ("verified", "approved"):
        item.status = "draft"
    item.version += 1
    record_audit(db, actor_id=user.id, action="manufacturing_facility.update", entity_type="manufacturing_facility", entity_id=item.id,
                 summary=f"Manufacturing facility updated: {item.name}")
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}")
def delete(item_id: str, user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
    item = db.get(ManufacturingFacility, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Manufacturing facility not found.")
    if item.status != "draft":
        raise HTTPException(status_code=400, detail="Only a draft record can be permanently deleted - archive it instead.")
    record_audit(db, actor_id=user.id, action="manufacturing_facility.delete", entity_type="manufacturing_facility", entity_id=item.id,
                 summary=f"Manufacturing facility deleted: {item.name}")
    db.delete(item)
    db.commit()
    return {"ok": True}
