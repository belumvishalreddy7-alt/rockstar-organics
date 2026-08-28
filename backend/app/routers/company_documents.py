"""
Company certificates & official documents.

Uploaded -> Under Review -> Verified -> Published, per the spec: uploading a
file never makes it verified or public by itself. The public list only ever
returns documents that are both verification_status == "verified" and
is_published == True.
"""
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.permissions import CONTENT_VERIFIERS, SETTINGS_MANAGERS
from app.core.deps import require_roles
from app.models.models import CompanyDocument, User
from app.schemas.schemas import CompanyDocumentCreate, CompanyDocumentReview

router = APIRouter(prefix="/api/v1/company/documents", tags=["company-documents"])

VALID_VERIFICATION_STATUSES = {"uploaded", "under_review", "verified", "rejected"}


def _public_shape(d: CompanyDocument) -> dict:
    return {
        "id": d.id, "title": d.title, "document_type": d.document_type,
        "reference_number": d.reference_number, "issuing_authority": d.issuing_authority,
        "issue_date": d.issue_date.isoformat() if d.issue_date else None,
        "expiry_date": d.expiry_date.isoformat() if d.expiry_date else None,
        "verification_status": d.verification_status,
        "download_url": f"/api/v1/media/certificates/{d.id}",
    }


def _admin_shape(d: CompanyDocument) -> dict:
    base = _public_shape(d)
    base.update({
        "is_published": d.is_published, "notes": d.notes,
        "uploaded_by_id": d.uploaded_by_id, "reviewed_by_id": d.reviewed_by_id,
        "reviewed_at": d.reviewed_at.isoformat() if d.reviewed_at else None,
        "submitted_by_id": d.submitted_by_id,
        "submitted_at": d.submitted_at.isoformat() if d.submitted_at else None,
        "rejection_reason": d.rejection_reason,
        "is_approved": d.is_approved,
        "approved_by_id": d.approved_by_id,
        "approved_at": d.approved_at.isoformat() if d.approved_at else None,
        "published_by_id": d.published_by_id,
        "published_at": d.published_at.isoformat() if d.published_at else None,
        "is_archived": d.is_archived,
        "archived_at": d.archived_at.isoformat() if d.archived_at else None,
        "version": d.version,
        "created_at": d.created_at.isoformat(), "updated_at": d.updated_at.isoformat(),
    })
    return base


@router.get("")
def list_public_documents(document_type: str | None = None, db: Session = Depends(get_db)):
    query = db.query(CompanyDocument).filter(
        CompanyDocument.is_published == True, CompanyDocument.verification_status == "verified",  # noqa: E712
        CompanyDocument.is_archived == False,  # noqa: E712
    )
    if document_type:
        query = query.filter(CompanyDocument.document_type == document_type)
    return [_public_shape(d) for d in query.order_by(CompanyDocument.created_at.desc()).all()]


@router.get("/admin")
def list_all_documents(user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    items = db.query(CompanyDocument).order_by(CompanyDocument.created_at.desc()).all()
    return [_admin_shape(d) for d in items]


@router.post("")
def create_document(payload: CompanyDocumentCreate, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    now = dt.datetime.utcnow()
    doc = CompanyDocument(**payload.model_dump(), uploaded_by_id=user.id, verification_status="uploaded", is_published=False,
                           submitted_by_id=user.id, submitted_at=now)
    db.add(doc)
    db.flush()
    record_audit(db, actor_id=user.id, action="company_document.create", entity_type="company_document", entity_id=doc.id,
                 summary=f"Company document uploaded: {doc.title}")
    db.commit()
    db.refresh(doc)
    return _admin_shape(doc)


@router.post("/{document_id}/verify/{status}")
def set_verification_status(document_id: str, status: str, payload: CompanyDocumentReview,
                             user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    if status not in VALID_VERIFICATION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid verification status.")
    doc = db.get(CompanyDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc.verification_status = status
    doc.reviewed_by_id = user.id
    doc.reviewed_at = dt.datetime.utcnow()
    if payload.notes:
        doc.notes = payload.notes
    if status == "rejected":
        doc.rejection_reason = payload.rejection_reason or payload.notes
    if status != "verified":
        # Never leave a published/approved doc in an unverified state -
        # re-verification always starts the approval gate over.
        doc.is_published = False
        doc.is_approved = False
    doc.version += 1
    record_audit(db, actor_id=user.id, action="company_document.verify", entity_type="company_document", entity_id=doc.id,
                 summary=f"Document {doc.title} verification set to {status}")
    db.commit()
    return _admin_shape(doc)


@router.post("/{document_id}/approve")
def approve_document(document_id: str, user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
    """A separate, administrator-only gate between verification and
    publication - a content verifier can confirm a document is genuine,
    but only Super Administrator/Administrator can authorize it for the
    public site."""
    doc = db.get(CompanyDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.verification_status != "verified":
        raise HTTPException(status_code=400, detail="Only verified documents can be approved.")
    doc.is_approved = True
    doc.approved_by_id = user.id
    doc.approved_at = dt.datetime.utcnow()
    doc.version += 1
    record_audit(db, actor_id=user.id, action="company_document.approve", entity_type="company_document", entity_id=doc.id,
                 summary=f"Document {doc.title} approved for publication")
    db.commit()
    return _admin_shape(doc)


@router.post("/{document_id}/publish")
def publish_document(document_id: str, user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
    doc = db.get(CompanyDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.verification_status != "verified" or not doc.is_approved:
        raise HTTPException(status_code=400, detail="Only verified and approved documents can be published.")
    if doc.is_archived:
        raise HTTPException(status_code=400, detail="An archived document must be unarchived before it can be published.")
    doc.is_published = True
    doc.published_by_id = user.id
    doc.published_at = dt.datetime.utcnow()
    record_audit(db, actor_id=user.id, action="company_document.publish", entity_type="company_document", entity_id=doc.id,
                 summary=f"Document {doc.title} published")
    db.commit()
    return _admin_shape(doc)


@router.post("/{document_id}/unpublish")
def unpublish_document(document_id: str, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    doc = db.get(CompanyDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc.is_published = False
    record_audit(db, actor_id=user.id, action="company_document.unpublish", entity_type="company_document", entity_id=doc.id,
                 summary=f"Document {doc.title} unpublished")
    db.commit()
    return _admin_shape(doc)


@router.post("/{document_id}/archive")
def archive_document(document_id: str, user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
    doc = db.get(CompanyDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc.is_archived = True
    doc.archived_at = dt.datetime.utcnow()
    doc.is_published = False  # archiving always removes it from the public site
    record_audit(db, actor_id=user.id, action="company_document.archive", entity_type="company_document", entity_id=doc.id,
                 summary=f"Document {doc.title} archived")
    db.commit()
    return _admin_shape(doc)


@router.post("/{document_id}/unarchive")
def unarchive_document(document_id: str, user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
    doc = db.get(CompanyDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc.is_archived = False
    doc.archived_at = None
    record_audit(db, actor_id=user.id, action="company_document.unarchive", entity_type="company_document", entity_id=doc.id,
                 summary=f"Document {doc.title} unarchived")
    db.commit()
    return _admin_shape(doc)
