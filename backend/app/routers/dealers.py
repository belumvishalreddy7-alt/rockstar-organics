import datetime as dt
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_roles, require_user
from app.core.email import application_approved_email, send_email
from app.core.notify import notify
from app.core.permissions import DEALER_MANAGERS, ROLE_DEALER
from app.core.rate_limit import rate_limiter
from app.core.references import generate_reference
from app.core.security import generate_token, hash_password
from app.models.models import DealerApplication, DealerProfile, DealerServiceArea, DealerProductAvailability, Product, User
from app.schemas.schemas import DealerApplicationCreate, DealerApplicationDecision, DealerProfileUpdate

router = APIRouter(prefix="/api/v1/dealers", tags=["dealers"])
settings = get_settings()


@router.post("/apply")
def submit_application(payload: DealerApplicationCreate, db: Session = Depends(get_db)):
    if not rate_limiter.check(f"dealer_apply:{payload.email.lower()}", settings.PUBLIC_FORM_RATE_LIMIT_ATTEMPTS, settings.PUBLIC_FORM_RATE_LIMIT_WINDOW_SECONDS):
        raise HTTPException(status_code=429, detail="Too many submissions. Please try again later.")

    duplicate = db.query(DealerApplication).filter(
        DealerApplication.email == payload.email.lower(), DealerApplication.status.in_(["new", "under_review", "information_required", "contacted", "on_hold"])
    ).first()
    application = DealerApplication(
        **{**payload.model_dump(), "email": payload.email.lower()},
        reference_number=generate_reference("DLR"),
        status="new",
    )
    db.add(application)
    db.flush()
    summary = f"Dealer application submitted: {application.business_name}"
    if duplicate:
        summary += " (duplicate of an existing open application; needs staff resolution)"
    record_audit(db, actor_id=None, action="dealer_application.submit", entity_type="dealer_application", entity_id=application.id, summary=summary)
    db.commit()
    db.refresh(application)
    return {"id": application.id, "reference_number": application.reference_number, "status": application.status, "duplicate_warning": bool(duplicate)}


@router.get("/applications")
def list_applications(status: str | None = None, user: User = Depends(require_roles(*DEALER_MANAGERS)), db: Session = Depends(get_db)):
    query = db.query(DealerApplication)
    if status:
        query = query.filter(DealerApplication.status == status)
    items = query.order_by(DealerApplication.created_at.desc()).all()
    return [
        {"id": a.id, "reference_number": a.reference_number, "business_name": a.business_name, "district": a.district,
         "status": a.status, "created_at": a.created_at.isoformat()}
        for a in items
    ]


@router.get("/applications/{application_id}")
def get_application(application_id: str, user: User = Depends(require_roles(*DEALER_MANAGERS)), db: Session = Depends(get_db)):
    a = db.get(DealerApplication, application_id)
    if not a:
        raise HTTPException(status_code=404, detail="Application not found.")
    return {c.name: getattr(a, c.name) for c in a.__table__.columns}


@router.post("/applications/{application_id}/status/{new_status}")
def change_application_status(application_id: str, new_status: str, payload: DealerApplicationDecision,
                               user: User = Depends(require_roles(*DEALER_MANAGERS)), db: Session = Depends(get_db)):
    valid = {"new", "under_review", "information_required", "contacted", "on_hold", "approved", "rejected", "withdrawn"}
    if new_status not in valid:
        raise HTTPException(status_code=400, detail="Invalid status.")
    a = db.get(DealerApplication, application_id)
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
        dealer_user = User(email=a.email, password_hash=hash_password(temp_password), role=ROLE_DEALER,
                            full_name=a.contact_person, phone=a.phone, status="active", must_change_password=True)
        db.add(dealer_user)
        db.flush()
        profile = DealerProfile(user_id=dealer_user.id, application_id=a.id, business_name=a.business_name,
                                 public_phone=a.phone, public_email=a.email, address=a.address, district=a.district)
        db.add(profile)
        db.flush()
        db.add(DealerServiceArea(dealer_id=profile.id, district=a.district, mandal=a.mandal))
        notify(db, recipient_id=dealer_user.id, type="dealer_application_approved", title="Application approved",
               message="Your dealer application has been approved. Sign in and change your temporary password.")
        created_credentials = {"email": dealer_user.email, "temporary_password": temp_password}

        html, text = application_approved_email(a.contact_person, a.business_name, dealer_user.email, temp_password, "Dealer")
        email_result = send_email(to=a.email, subject="Your Rockstar Organics dealer application has been approved", html=html, text=text)
        if not email_result.sent:
            created_credentials["email_delivery"] = email_result.error or "Email provider not configured; deliver credentials to the applicant directly."

    record_audit(db, actor_id=user.id, action="dealer_application.status_change", entity_type="dealer_application",
                 entity_id=a.id, summary=f"Application {a.reference_number} -> {new_status}")
    db.commit()
    result = {"id": a.id, "status": a.status}
    if created_credentials:
        result["dealer_credentials"] = created_credentials
    return result


@router.get("/directory")
def public_directory(district: str | None = None, mandal: str | None = None, product_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(DealerProfile).filter(DealerProfile.directory_opt_in == True, DealerProfile.suspended == False)  # noqa: E712
    if district:
        query = query.filter(DealerProfile.district == district)
    dealers = query.all()
    out = []
    for d in dealers:
        if mandal and not any(sa.mandal == mandal for sa in d.service_areas):
            continue
        if product_id:
            avail = db.query(DealerProductAvailability).filter(DealerProductAvailability.dealer_id == d.id, DealerProductAvailability.product_id == product_id, DealerProductAvailability.status.in_(["available", "limited"])).first()
            if not avail:
                continue
        out.append({
            "id": d.id, "business_name": d.business_name, "district": d.district,
            "service_areas": [{"district": sa.district, "mandal": sa.mandal} for sa in d.service_areas],
            "public_phone": d.public_phone if d.show_public_phone else None,
            "public_email": d.public_email if d.show_public_email else None,
            "last_activity_at": d.last_activity_at.isoformat() if d.last_activity_at else None,
        })
    return out


@router.get("/me/profile")
def my_dealer_profile(user: User = Depends(require_roles(ROLE_DEALER)), db: Session = Depends(get_db)):
    profile = db.query(DealerProfile).filter(DealerProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Dealer profile not found.")
    return {
        "id": profile.id, "business_name": profile.business_name, "district": profile.district,
        "directory_opt_in": profile.directory_opt_in, "farmer_case_opt_in": profile.farmer_case_opt_in,
        "show_public_phone": profile.show_public_phone, "show_public_email": profile.show_public_email,
        "public_phone": profile.public_phone, "public_email": profile.public_email,
        "service_areas": [{"id": sa.id, "district": sa.district, "mandal": sa.mandal} for sa in profile.service_areas],
    }


@router.put("/me/profile")
def update_my_dealer_profile(payload: DealerProfileUpdate, user: User = Depends(require_roles(ROLE_DEALER)), db: Session = Depends(get_db)):
    profile = db.query(DealerProfile).filter(DealerProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Dealer profile not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    profile.last_activity_at = dt.datetime.utcnow()
    record_audit(db, actor_id=user.id, action="dealer.profile_update", entity_type="dealer_profile", entity_id=profile.id, summary="Dealer updated their profile")
    db.commit()
    return {"ok": True}


@router.post("/me/availability/{product_id}/{status}")
def set_availability(product_id: str, status: str, notes: str | None = None,
                      user: User = Depends(require_roles(ROLE_DEALER)), db: Session = Depends(get_db)):
    if status not in {"available", "limited", "unavailable", "unknown"}:
        raise HTTPException(status_code=400, detail="Invalid availability status.")
    product = db.get(Product, product_id)
    if not product or product.status != "published":
        raise HTTPException(status_code=400, detail="Only published products may have availability declared.")
    profile = db.query(DealerProfile).filter(DealerProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Dealer profile not found.")
    record = db.query(DealerProductAvailability).filter(DealerProductAvailability.dealer_id == profile.id, DealerProductAvailability.product_id == product_id).first()
    if not record:
        record = DealerProductAvailability(dealer_id=profile.id, product_id=product_id)
        db.add(record)
    record.status = status
    record.notes = notes
    record.confirmed_at = dt.datetime.utcnow()
    profile.last_activity_at = dt.datetime.utcnow()
    db.commit()
    return {"ok": True}
