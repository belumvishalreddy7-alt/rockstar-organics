"""Shared status-workflow endpoints for the corporate-content CMS entities
(leadership, manufacturing, research, certifications, sustainability - see
app.models.models.VerifiableMixin). Every one of those models carries the
exact same status/audit columns, so the transitions below are written once
and attached to each domain's router via register_workflow_routes() rather
than copy-pasted per domain.

Flow: draft -> submitted -> under_review -> verified / rejected -> approved
-> published -> archived. Creating/editing/verifying content is a
CONTENT_VERIFIERS action (owner/admin/content_manager - the same "owner +
managers" set already used for products); approving, publishing and
archiving are SETTINGS_MANAGERS-only (owner/admin), matching the existing
company_documents.py split between a verifier and a publisher.
"""
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.permissions import CONTENT_VERIFIERS, SETTINGS_MANAGERS
from app.models.models import User
from app.schemas.schemas import WorkflowActionNote


def register_workflow_routes(router: APIRouter, model, *, entity_type: str, label_field: str) -> None:
    def _get_or_404(db: Session, item_id: str):
        item = db.get(model, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Record not found.")
        return item

    def _label(item) -> str:
        return getattr(item, label_field, item.id)

    def _audit(db: Session, user: User, item, action: str, summary: str) -> None:
        record_audit(db, actor_id=user.id, action=f"{entity_type}.{action}", entity_type=entity_type, entity_id=item.id, summary=summary)

    @router.post("/{item_id}/submit")
    def submit(item_id: str, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
        item = _get_or_404(db, item_id)
        if item.status not in ("draft", "rejected"):
            raise HTTPException(status_code=400, detail=f"Cannot submit from status '{item.status}'.")
        item.status = "submitted"
        item.submitted_by_id = user.id
        item.submitted_at = dt.datetime.utcnow()
        item.version += 1
        _audit(db, user, item, "submit", f"{_label(item)} submitted for review")
        db.commit()
        return {"id": item.id, "status": item.status}

    @router.post("/{item_id}/review")
    def start_review(item_id: str, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
        item = _get_or_404(db, item_id)
        if item.status != "submitted":
            raise HTTPException(status_code=400, detail="Only a submitted record can move to under review.")
        item.status = "under_review"
        item.reviewer_id = user.id
        item.version += 1
        _audit(db, user, item, "review", f"{_label(item)} moved to under review")
        db.commit()
        return {"id": item.id, "status": item.status}

    @router.post("/{item_id}/verify")
    def verify(item_id: str, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
        item = _get_or_404(db, item_id)
        if item.status not in ("under_review", "submitted"):
            raise HTTPException(status_code=400, detail="Only an under-review record can be verified.")
        item.status = "verified"
        item.reviewer_id = user.id
        item.verified_at = dt.datetime.utcnow()
        item.version += 1
        _audit(db, user, item, "verify", f"{_label(item)} verified")
        db.commit()
        return {"id": item.id, "status": item.status}

    @router.post("/{item_id}/reject")
    def reject(item_id: str, payload: WorkflowActionNote = WorkflowActionNote(),
               user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
        item = _get_or_404(db, item_id)
        if item.status not in ("under_review", "verified"):
            raise HTTPException(status_code=400, detail="Only an under-review or verified record can be rejected.")
        item.status = "rejected"
        item.reviewer_id = user.id
        item.rejection_reason = payload.note
        item.version += 1
        _audit(db, user, item, "reject", f"{_label(item)} rejected")
        db.commit()
        return {"id": item.id, "status": item.status}

    @router.post("/{item_id}/request-revision")
    def request_revision(item_id: str, payload: WorkflowActionNote = WorkflowActionNote(),
                          user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
        item = _get_or_404(db, item_id)
        if item.status in ("published", "archived"):
            raise HTTPException(status_code=400, detail=f"Cannot request revision from status '{item.status}'.")
        item.status = "draft"
        item.reviewer_id = user.id
        item.rejection_reason = payload.note
        item.version += 1
        _audit(db, user, item, "request_revision", f"{_label(item)} sent back for revision")
        db.commit()
        return {"id": item.id, "status": item.status}

    @router.post("/{item_id}/approve")
    def approve(item_id: str, user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
        item = _get_or_404(db, item_id)
        if item.status != "verified":
            raise HTTPException(status_code=400, detail="Only a verified record can be approved.")
        item.status = "approved"
        item.approved_by_id = user.id
        item.approved_at = dt.datetime.utcnow()
        item.version += 1
        _audit(db, user, item, "approve", f"{_label(item)} approved for publication")
        db.commit()
        return {"id": item.id, "status": item.status}

    @router.post("/{item_id}/publish")
    def publish(item_id: str, user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
        item = _get_or_404(db, item_id)
        if item.status != "approved":
            raise HTTPException(status_code=400, detail="Only an approved record can be published.")
        item.status = "published"
        item.published_by_id = user.id
        item.published_at = dt.datetime.utcnow()
        item.version += 1
        _audit(db, user, item, "publish", f"{_label(item)} published")
        db.commit()
        return {"id": item.id, "status": item.status}

    @router.post("/{item_id}/unpublish")
    def unpublish(item_id: str, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
        item = _get_or_404(db, item_id)
        if item.status != "published":
            raise HTTPException(status_code=400, detail="Only a published record can be unpublished.")
        item.status = "approved"
        item.version += 1
        _audit(db, user, item, "unpublish", f"{_label(item)} unpublished")
        db.commit()
        return {"id": item.id, "status": item.status}

    @router.post("/{item_id}/archive")
    def archive(item_id: str, user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
        item = _get_or_404(db, item_id)
        if item.status == "archived":
            raise HTTPException(status_code=400, detail="Already archived.")
        item.status = "archived"
        item.version += 1
        _audit(db, user, item, "archive", f"{_label(item)} archived")
        db.commit()
        return {"id": item.id, "status": item.status}

    @router.post("/{item_id}/restore")
    def restore(item_id: str, user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
        """Brings an archived record back to draft so it can re-enter the
        workflow. This app does not keep field-level historical snapshots,
        so "restore" reactivates the record rather than reverting its
        content to a prior version - see audit_logs for the full change
        history of every transition."""
        item = _get_or_404(db, item_id)
        if item.status != "archived":
            raise HTTPException(status_code=400, detail="Only an archived record can be restored.")
        item.status = "draft"
        item.version += 1
        _audit(db, user, item, "restore", f"{_label(item)} restored from archive")
        db.commit()
        return {"id": item.id, "status": item.status}
