"""
Distributor portal: Registration -> Verification -> Approval -> Activation.

Mirrors app/routers/dealers.py's application workflow exactly (see that
file's comments for the general pattern) but for the Distributor role and
DistributorProfile/DistributorStock tables. Kept as a separate router
rather than merged into dealers.py because dealers and distributors are
distinct business relationships in the spec (dealer = retail/farmer-facing
stock; distributor = territory/warehouse-level).
"""
import datetime as dt
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.email import application_approved_email, send_email
from app.core.notify import notify
from app.core.permissions import DISTRIBUTOR_MANAGERS, ROLE_DISTRIBUTOR
from app.core.rate_limit import rate_limiter
from app.core.references import generate_reference
from app.core.security import hash_password
from app.models.models import DistributorApplication, DistributorProfile, DistributorStock, Product, User
from app.schemas.schemas import DistributorApplicationCreate, DistributorApplicationDecision, DistributorProfileUpdate

router = APIRouter(prefix="/api/v1/distributors", tags=["distributors"])
settings = get_settings()

VALID_STATUSES = {"new", "under_review", "information_required", "contacted", "on_hold", "approved", "rejected", "withdrawn"}


@router.post("/apply")
def submit_application(payload: DistributorApplicationCreate, db: Session = Depends(get_db)):
    if not rate_limiter.check(f"distributor_apply:{payload.email.lower()}", settings.PUBLIC_FORM_RATE_LIMIT_ATTEMPTS, settings.PUBLIC_FORM_RATE_LIMIT_WINDOW_SECONDS):
        raise HTTPException(status_code=429, detail="Too many submissions. Please try again later.")

    duplicate = db.query(DistributorApplication).filter(
        DistributorApplication.email == payload.email.lower(),
        DistributorApplication.status.in_(["new", "under_review", "information_required", "contacted", "on_hold"]),
    ).first()
    application = DistributorApplication(
        **{**payload.model_dump(), "email": payload.email.lower()},
        reference_number=generate_reference("DST"),
        status="new",
    )
    db.add(application)
    db.flush()
    summary = f"Distributor application submitted: {application.business_name}"
    if duplicate:
        summary += " (duplicate of an existing open application; needs staff resolution)"
    record_audit(db, actor_id=None, action="distributor_application.submit", entity_type="distributor_application",
                 entity_id=application.id, summary=summary)
    db.commit()
    db.refresh(application)
    return {"id": application.id, "reference_number": application.reference_number, "status": application.status, "duplicate_warning": bool(duplicate)}


@router.get("/applications")
def list_applications(status: str | None = None, user: User = Depends(require_roles(*DISTRIBUTOR_MANAGERS)), db: Session = Depends(get_db)):
    query = db.query(DistributorApplication)
    if status:
        query = query.filter(DistributorApplication.status == status)
    items = query.order_by(DistributorApplication.created_at.desc()).all()
    return [
        {"id": a.id, "reference_number": a.reference_number, "business_name": a.business_name, "territory": a.territory,
         "phone": a.phone, "status": a.status, "created_at": a.created_at.isoformat()}
        for a in items
    ]


@router.get("/applications/{application_id}")
def get_application(application_id: str, user: User = Depends(require_roles(*DISTRIBUTOR_MANAGERS)), db: Session = Depends(get_db)):
    a = db.get(DistributorApplication, application_id)
    if not a:
        raise HTTPException(status_code=404, detail="Application not found.")
    return {c.name: getattr(a, c.name) for c in a.__table__.columns}


@router.post("/applications/{application_id}/status/{new_status}")
def change_application_status(application_id: str, new_status: str, payload: DistributorApplicationDecision,
                               user: User = Depends(require_roles(*DISTRIBUTOR_MANAGERS)), db: Session = Depends(get_db)):
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status.")
    a = db.get(DistributorApplication, application_id)
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

    created_credentials = None
    if new_status == "approved":
        existing_user = db.query(User).filter(User.email == a.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="A user account with this email already exists; resolve manually before approving.")
        temp_password = secrets.token_urlsafe(9)
        distributor_user = User(email=a.email, password_hash=hash_password(temp_password), role=ROLE_DISTRIBUTOR,
                                 full_name=a.contact_person, phone=a.phone, status="active", must_change_password=True)
        db.add(distributor_user)
        db.flush()
        # Same reasoning as the dealer approval flow (see dealers.py): the
        # owner approving IS the "make this findable" decision, so opted
        # into the public directory by default rather than requiring a
        # separate self-service step - a distributor can still opt back out
        # via PUT /distributors/me/profile.
        profile = DistributorProfile(user_id=distributor_user.id, application_id=a.id, business_name=a.business_name,
                                      territory=a.territory, public_phone=a.phone, public_email=a.email, address=a.address,
                                      directory_opt_in=True, show_public_phone=True, show_public_email=True)
        db.add(profile)
        notify(db, recipient_id=distributor_user.id, type="distributor_application_approved", title="Application approved",
               message="Your distributor application has been approved. Sign in and change your temporary password.")
        created_credentials = {"email": distributor_user.email, "temporary_password": temp_password}

        html, text = application_approved_email(a.contact_person, a.business_name, distributor_user.email, temp_password, "Distributor")
        email_result = send_email(to=a.email, subject="Your Rockstar Organics distributor application has been approved", html=html, text=text)
        if not email_result.sent:
            created_credentials["email_delivery"] = email_result.error or "Email provider not configured; deliver credentials to the applicant directly."

    record_audit(db, actor_id=user.id, action="distributor_application.status_change", entity_type="distributor_application",
                 entity_id=a.id, summary=f"Application {a.reference_number} -> {new_status}")
    db.commit()
    result = {"id": a.id, "status": a.status}
    if created_credentials:
        result["distributor_credentials"] = created_credentials
    return result


@router.get("/directory")
def public_directory(territory: str | None = None, db: Session = Depends(get_db)):
    query = db.query(DistributorProfile).filter(DistributorProfile.directory_opt_in == True, DistributorProfile.suspended == False)  # noqa: E712
    if territory:
        query = query.filter(DistributorProfile.territory == territory)
    return [
        {
            "id": d.id, "business_name": d.business_name, "territory": d.territory,
            "public_phone": d.public_phone if d.show_public_phone else None,
            "public_email": d.public_email if d.show_public_email else None,
            "last_activity_at": d.last_activity_at.isoformat() if d.last_activity_at else None,
        }
        for d in query.all()
    ]


@router.get("/me/profile")
def my_profile(user: User = Depends(require_roles(ROLE_DISTRIBUTOR)), db: Session = Depends(get_db)):
    profile = db.query(DistributorProfile).filter(DistributorProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Distributor profile not found.")
    return {
        "id": profile.id, "business_name": profile.business_name, "territory": profile.territory,
        "public_phone": profile.public_phone, "public_email": profile.public_email, "address": profile.address,
        "directory_opt_in": profile.directory_opt_in, "show_public_phone": profile.show_public_phone,
        "show_public_email": profile.show_public_email, "suspended": profile.suspended,
    }


@router.put("/me/profile")
def update_my_profile(payload: DistributorProfileUpdate, user: User = Depends(require_roles(ROLE_DISTRIBUTOR)), db: Session = Depends(get_db)):
    profile = db.query(DistributorProfile).filter(DistributorProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Distributor profile not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    profile.last_activity_at = dt.datetime.utcnow()
    record_audit(db, actor_id=user.id, action="distributor.profile_update", entity_type="distributor_profile", entity_id=profile.id,
                 summary="Distributor updated their profile")
    db.commit()
    return {"ok": True}


@router.post("/me/stock/{product_id}/{status}")
def set_stock(product_id: str, status: str, quantity_note: str | None = None,
              user: User = Depends(require_roles(ROLE_DISTRIBUTOR)), db: Session = Depends(get_db)):
    if status not in {"available", "limited", "unavailable", "unknown"}:
        raise HTTPException(status_code=400, detail="Invalid stock status.")
    product = db.get(Product, product_id)
    if not product or product.status != "published":
        raise HTTPException(status_code=400, detail="Only published products may have stock declared.")
    profile = db.query(DistributorProfile).filter(DistributorProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Distributor profile not found.")
    record = db.query(DistributorStock).filter(DistributorStock.distributor_id == profile.id, DistributorStock.product_id == product_id).first()
    if not record:
        record = DistributorStock(distributor_id=profile.id, product_id=product_id)
        db.add(record)
    record.status = status
    record.quantity_note = quantity_note
    profile.last_activity_at = dt.datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.get("/me/stock")
def list_my_stock(user: User = Depends(require_roles(ROLE_DISTRIBUTOR)), db: Session = Depends(get_db)):
    profile = db.query(DistributorProfile).filter(DistributorProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Distributor profile not found.")
    items = db.query(DistributorStock).filter(DistributorStock.distributor_id == profile.id).all()
    return [{"product_id": s.product_id, "status": s.status, "quantity_note": s.quantity_note, "updated_at": s.updated_at.isoformat()} for s in items]
