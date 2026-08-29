"""Research & Development: research facilities and research-area cards.
See app.core.verifiable_workflow for the shared status transitions. A
category may exist as an empty admin-managed card, but nothing here claims
Rockstar Organics performs research in it until a real record is verified
and published."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.permissions import CONTENT_VERIFIERS, SETTINGS_MANAGERS
from app.core.verifiable_workflow import register_workflow_routes
from app.models.models import ResearchArea, ResearchFacility, User
from app.schemas.schemas import ResearchAreaCreate, ResearchAreaOut, ResearchFacilityCreate, ResearchFacilityOut

facilities_router = APIRouter(prefix="/api/v1/research/facilities", tags=["research"])
register_workflow_routes(facilities_router, ResearchFacility, entity_type="research_facility", label_field="name")

areas_router = APIRouter(prefix="/api/v1/research/areas", tags=["research"])
register_workflow_routes(areas_router, ResearchArea, entity_type="research_area", label_field="title")


# --- Facilities -----------------------------------------------------------

@facilities_router.get("/public", response_model=list[ResearchFacilityOut])
def list_facilities_public(db: Session = Depends(get_db)):
    return db.query(ResearchFacility).filter(ResearchFacility.status == "published").order_by(ResearchFacility.name).all()


@facilities_router.get("/public/{item_id}", response_model=ResearchFacilityOut)
def get_facility_public(item_id: str, db: Session = Depends(get_db)):
    item = db.get(ResearchFacility, item_id)
    if not item or item.status != "published":
        raise HTTPException(status_code=404, detail="Research facility not found.")
    return item


@facilities_router.get("/admin", response_model=list[ResearchFacilityOut])
def list_facilities_admin(user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    return db.query(ResearchFacility).order_by(ResearchFacility.created_at.desc()).all()


@facilities_router.post("", response_model=ResearchFacilityOut)
def create_facility(payload: ResearchFacilityCreate, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    item = ResearchFacility(**payload.model_dump(), created_by_id=user.id, updated_by_id=user.id)
    db.add(item)
    db.flush()
    record_audit(db, actor_id=user.id, action="research_facility.create", entity_type="research_facility", entity_id=item.id,
                 summary=f"Research facility created: {item.name}")
    db.commit()
    db.refresh(item)
    return item


@facilities_router.put("/{item_id}", response_model=ResearchFacilityOut)
def update_facility(item_id: str, payload: ResearchFacilityCreate, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    item = db.get(ResearchFacility, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Research facility not found.")
    if item.status == "published":
        raise HTTPException(status_code=400, detail="Unpublish before editing a published facility.")
    for field, value in payload.model_dump().items():
        setattr(item, field, value)
    item.updated_by_id = user.id
    if item.status in ("verified", "approved"):
        item.status = "draft"
    item.version += 1
    record_audit(db, actor_id=user.id, action="research_facility.update", entity_type="research_facility", entity_id=item.id,
                 summary=f"Research facility updated: {item.name}")
    db.commit()
    db.refresh(item)
    return item


@facilities_router.delete("/{item_id}")
def delete_facility(item_id: str, user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
    item = db.get(ResearchFacility, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Research facility not found.")
    if item.status != "draft":
        raise HTTPException(status_code=400, detail="Only a draft record can be permanently deleted - archive it instead.")
    record_audit(db, actor_id=user.id, action="research_facility.delete", entity_type="research_facility", entity_id=item.id,
                 summary=f"Research facility deleted: {item.name}")
    db.delete(item)
    db.commit()
    return {"ok": True}


# --- Research areas ---------------------------------------------------------

@areas_router.get("/public", response_model=list[ResearchAreaOut])
def list_areas_public(db: Session = Depends(get_db)):
    return db.query(ResearchArea).filter(ResearchArea.status == "published").order_by(ResearchArea.sort_order, ResearchArea.title).all()


@areas_router.get("/admin", response_model=list[ResearchAreaOut])
def list_areas_admin(user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    return db.query(ResearchArea).order_by(ResearchArea.sort_order, ResearchArea.created_at.desc()).all()


@areas_router.post("", response_model=ResearchAreaOut)
def create_area(payload: ResearchAreaCreate, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    item = ResearchArea(**payload.model_dump(), created_by_id=user.id, updated_by_id=user.id)
    db.add(item)
    db.flush()
    record_audit(db, actor_id=user.id, action="research_area.create", entity_type="research_area", entity_id=item.id,
                 summary=f"Research area created: {item.title}")
    db.commit()
    db.refresh(item)
    return item


@areas_router.put("/{item_id}", response_model=ResearchAreaOut)
def update_area(item_id: str, payload: ResearchAreaCreate, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    item = db.get(ResearchArea, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Research area not found.")
    if item.status == "published":
        raise HTTPException(status_code=400, detail="Unpublish before editing a published research area.")
    for field, value in payload.model_dump().items():
        setattr(item, field, value)
    item.updated_by_id = user.id
    if item.status in ("verified", "approved"):
        item.status = "draft"
    item.version += 1
    record_audit(db, actor_id=user.id, action="research_area.update", entity_type="research_area", entity_id=item.id,
                 summary=f"Research area updated: {item.title}")
    db.commit()
    db.refresh(item)
    return item


@areas_router.delete("/{item_id}")
def delete_area(item_id: str, user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
    item = db.get(ResearchArea, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Research area not found.")
    if item.status != "draft":
        raise HTTPException(status_code=400, detail="Only a draft record can be permanently deleted - archive it instead.")
    record_audit(db, actor_id=user.id, action="research_area.delete", entity_type="research_area", entity_id=item.id,
                 summary=f"Research area deleted: {item.title}")
    db.delete(item)
    db.commit()
    return {"ok": True}
