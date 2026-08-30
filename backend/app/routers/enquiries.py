from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_roles, require_user
from app.core.permissions import CASE_MANAGERS
from app.core.rate_limit import rate_limiter
from app.core.references import generate_reference
from app.models.models import Enquiry, User
from app.schemas.schemas import EnquiryCreate

router = APIRouter(prefix="/api/v1/enquiries", tags=["enquiries"])
settings = get_settings()


@router.post("")
def submit_enquiry(payload: EnquiryCreate, db: Session = Depends(get_db)):
    key = f"enquiry:{payload.email or payload.phone or 'anon'}"
    if not rate_limiter.check(key, settings.PUBLIC_FORM_RATE_LIMIT_ATTEMPTS, settings.PUBLIC_FORM_RATE_LIMIT_WINDOW_SECONDS):
        raise HTTPException(status_code=429, detail="Too many submissions. Please try again later.")
    if not payload.consent_given:
        raise HTTPException(status_code=400, detail="Consent is required.")

    e = Enquiry(**{k: v for k, v in payload.model_dump().items() if k != "consent_given"}, reference_number=generate_reference("ENQ"))
    db.add(e)
    db.flush()
    record_audit(db, actor_id=None, action="enquiry.submit", entity_type="enquiry", entity_id=e.id, summary=f"Enquiry {e.reference_number} submitted ({e.enquiry_type})")
    db.commit()
    return {"reference_number": e.reference_number}


@router.get("")
def list_enquiries(status: str | None = None, user: User = Depends(require_roles(*CASE_MANAGERS, "content_manager")), db: Session = Depends(get_db)):
    query = db.query(Enquiry)
    if status:
        query = query.filter(Enquiry.status == status)
    items = query.order_by(Enquiry.created_at.desc()).all()
    return [{"id": e.id, "reference_number": e.reference_number, "enquiry_type": e.enquiry_type, "name": e.name,
             "phone": e.phone, "status": e.status, "created_at": e.created_at.isoformat()} for e in items]


@router.post("/{enquiry_id}/assign/{staff_id}")
def assign_enquiry(enquiry_id: str, staff_id: str, user: User = Depends(require_roles(*CASE_MANAGERS)), db: Session = Depends(get_db)):
    e = db.get(Enquiry, enquiry_id)
    if not e:
        raise HTTPException(status_code=404, detail="Enquiry not found.")
    if not db.get(User, staff_id):
        raise HTTPException(status_code=404, detail="Staff member not found.")
    e.assigned_staff_id = staff_id
    e.status = "assigned"
    record_audit(db, actor_id=user.id, action="enquiry.assign", entity_type="enquiry", entity_id=e.id, summary=f"Enquiry {e.reference_number} assigned")
    db.commit()
    return {"ok": True}


@router.post("/{enquiry_id}/status/{new_status}")
def enquiry_status(enquiry_id: str, new_status: str, user: User = Depends(require_roles(*CASE_MANAGERS)), db: Session = Depends(get_db)):
    valid = {"new", "assigned", "in_progress", "waiting_for_customer", "resolved", "closed", "spam", "cancelled"}
    if new_status not in valid:
        raise HTTPException(status_code=400, detail="Invalid status.")
    e = db.get(Enquiry, enquiry_id)
    if not e:
        raise HTTPException(status_code=404, detail="Enquiry not found.")
    e.status = new_status
    record_audit(db, actor_id=user.id, action="enquiry.status_change", entity_type="enquiry", entity_id=e.id, summary=f"Enquiry {e.reference_number} -> {new_status}")
    db.commit()
    return {"ok": True}
