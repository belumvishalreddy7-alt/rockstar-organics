"""CMS-controlled overview text for the five corporate page sections
(leadership, manufacturing, research_development, quality_safety,
sustainability). One row per section, created lazily on first admin edit -
a section with no row, or a row not yet published, means the public page
falls back to "Information pending verification." (enforced by the
frontend, since the API simply returns 404/omits unpublished fields).

Reuses the same verification/approval/publication workflow as the
structured entities (see app.core.verifiable_workflow) so free-text
overview copy goes through the same owner/manager-gated review as
everything else, rather than being editable straight to the live site."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.permissions import CONTENT_VERIFIERS
from app.core.verifiable_workflow import register_workflow_routes
from app.models.models import CompanyPageContent, User
from app.schemas.schemas import CORPORATE_SECTIONS, CompanyPageContentOut, CompanyPageContentUpdate

router = APIRouter(prefix="/api/v1/company/pages", tags=["company-pages"])
register_workflow_routes(router, CompanyPageContent, entity_type="company_page_content", label_field="section")


def _get_or_404(db: Session, section: str) -> CompanyPageContent:
    if section not in CORPORATE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown page section.")
    item = db.query(CompanyPageContent).filter(CompanyPageContent.section == section).first()
    if not item:
        raise HTTPException(status_code=404, detail="No content has been entered for this section yet.")
    return item


@router.get("/public/{section}", response_model=CompanyPageContentOut)
def get_public(section: str, db: Session = Depends(get_db)):
    item = _get_or_404(db, section)
    if item.status != "published":
        raise HTTPException(status_code=404, detail="No published content for this section yet.")
    return item


@router.get("/admin/{section}", response_model=CompanyPageContentOut)
def get_admin(section: str, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    if section not in CORPORATE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown page section.")
    item = db.query(CompanyPageContent).filter(CompanyPageContent.section == section).first()
    if not item:
        # Lazily create an empty draft row so the admin UI always has
        # something to edit and submit, rather than a separate "create".
        item = CompanyPageContent(section=section, fields={}, created_by_id=user.id, updated_by_id=user.id)
        db.add(item)
        db.commit()
        db.refresh(item)
    return item


@router.put("/admin/{section}", response_model=CompanyPageContentOut)
def update(section: str, payload: CompanyPageContentUpdate, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    if section not in CORPORATE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown page section.")
    item = db.query(CompanyPageContent).filter(CompanyPageContent.section == section).first()
    if not item:
        item = CompanyPageContent(section=section, created_by_id=user.id)
        db.add(item)
        db.flush()
    if item.status == "published":
        raise HTTPException(status_code=400, detail="Unpublish before editing published content.")
    item.fields = payload.fields
    item.source_reference = payload.source_reference
    item.updated_by_id = user.id
    if item.status in ("verified", "approved"):
        item.status = "draft"
    item.version += 1
    record_audit(db, actor_id=user.id, action="company_page_content.update", entity_type="company_page_content", entity_id=item.id,
                 summary=f"{section} overview content updated")
    db.commit()
    db.refresh(item)
    return item
