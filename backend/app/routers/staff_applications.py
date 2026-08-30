"""Public employment applications for internal (staff-level) positions.
Submitting this form never creates a login by itself - see
app.models.models.StaffApplication's docstring. Only an existing owner/
admin (SETTINGS_MANAGERS, the same role set that already gates
staff.invite) can review and approve one, choosing the actual role to
grant at that moment rather than trusting the applicant's requested
position."""
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.notify import notify
from app.core.permissions import ROLE_SUPER_ADMIN, SETTINGS_MANAGERS, STAFF_ROLES
from app.core.rate_limit import rate_limiter
from app.core.references import generate_reference
from app.core.security import hash_password
from app.models.models import StaffApplication, User
from app.schemas.schemas import StaffApplicationApprove, StaffApplicationCreate, StaffApplicationDecision

router = APIRouter(prefix="/api/v1/staff-applications", tags=["staff-applications"])
settings = get_settings()

VALID_STATUSES = {"new", "under_review", "information_required", "contacted", "on_hold", "approved", "rejected", "withdrawn"}


@router.post("")
def submit_application(payload: StaffApplicationCreate, db: Session = Depends(get_db)):
    if not rate_limiter.check(f"staff_apply:{payload.email.lower()}", settings.PUBLIC_FORM_RATE_LIMIT_ATTEMPTS, settings.PUBLIC_FORM_RATE_LIMIT_WINDOW_SECONDS):
        raise HTTPException(status_code=429, detail="Too many submissions. Please try again later.")

    duplicate = db.query(StaffApplication).filter(
        StaffApplication.email == payload.email.lower(),
        StaffApplication.status.in_(["new", "under_review", "information_required", "contacted", "on_hold"]),
    ).first()
    application = StaffApplication(
        **{**payload.model_dump(), "email": payload.email.lower()},
        reference_number=generate_reference("EMP"),
        status="new",
    )
    db.add(application)
    db.flush()
    summary = f"Staff application submitted: {application.full_name} ({application.position_applied_for})"
    if duplicate:
        summary += " (duplicate of an existing open application; needs staff resolution)"
    record_audit(db, actor_id=None, action="staff_application.submit", entity_type="staff_application", entity_id=application.id, summary=summary)
    db.commit()
    db.refresh(application)
    return {"id": application.id, "reference_number": application.reference_number, "status": application.status, "duplicate_warning": bool(duplicate)}


@router.get("")
def list_applications(status: str | None = None, user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
    query = db.query(StaffApplication)
    if status:
        query = query.filter(StaffApplication.status == status)
    items = query.order_by(StaffApplication.created_at.desc()).all()
    return [
        {"id": a.id, "reference_number": a.reference_number, "full_name": a.full_name, "email": a.email,
         "phone": a.phone, "position_applied_for": a.position_applied_for, "status": a.status,
         "created_at": a.created_at.isoformat()}
        for a in items
    ]


@router.post("/{application_id}/status/{new_status}")
def change_status(application_id: str, new_status: str, payload: StaffApplicationDecision,
                   user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
    if new_status not in VALID_STATUSES or new_status == "approved":
        raise HTTPException(status_code=400, detail="Invalid status - use /approve to approve an application.")
    a = db.get(StaffApplication, application_id)
    if not a:
        raise HTTPException(status_code=404, detail="Application not found.")
    if a.status in ("approved", "rejected", "withdrawn"):
        raise HTTPException(status_code=400, detail=f"Application already {a.status}; no further status changes allowed.")

    a.status = new_status
    a.reviewer_id = user.id
    if new_status == "rejected":
        a.rejection_reason = payload.reason
    else:
        a.review_notes = payload.reason or a.review_notes
    record_audit(db, actor_id=user.id, action="staff_application.status_change", entity_type="staff_application",
                 entity_id=a.id, summary=f"Application {a.reference_number} -> {new_status}")
    db.commit()
    return {"id": a.id, "status": a.status}


@router.post("/{application_id}/approve")
def approve_application(application_id: str, payload: StaffApplicationApprove,
                         user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
    a = db.get(StaffApplication, application_id)
    if not a:
        raise HTTPException(status_code=404, detail="Application not found.")
    if a.status in ("approved", "rejected", "withdrawn"):
        raise HTTPException(status_code=400, detail=f"Application already {a.status}; no further status changes allowed.")
    if payload.role not in STAFF_ROLES:
        raise HTTPException(status_code=400, detail="Invalid staff role.")
    if payload.role == ROLE_SUPER_ADMIN and user.role != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only a Super Administrator can grant Super Administrator access.")
    if db.query(User).filter(User.email == a.email).first():
        raise HTTPException(status_code=400, detail="A user account with this email already exists; resolve manually before approving.")

    temp_password = secrets.token_urlsafe(9)
    staff_user = User(email=a.email, password_hash=hash_password(temp_password), role=payload.role,
                       full_name=a.full_name, phone=a.phone, status="active", must_change_password=True)
    db.add(staff_user)
    db.flush()

    a.status = "approved"
    a.reviewer_id = user.id
    notify(db, recipient_id=staff_user.id, type="staff_application_approved", title="Welcome to Rockstar Organics",
           message="Your employment application has been approved. Sign in and change your temporary password.")
    record_audit(db, actor_id=user.id, action="staff_application.approve", entity_type="staff_application", entity_id=a.id,
                 summary=f"Staff application {a.reference_number} approved as {payload.role}: {staff_user.email}")
    db.commit()
    return {"id": a.id, "status": a.status, "staff_credentials": {"email": staff_user.email, "temporary_password": temp_password}}
