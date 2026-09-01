"""
Account status management for farmer and dealer accounts (staff account
status is handled separately in routers/staff.py, which also enforces the
"cannot grant Super Administrator" rule).

This closes a real gap: the original build had no way for an administrator
to suspend a farmer or dealer account at all - "Active, Pending, Suspended,
Rejected, Disabled statuses" from the spec were modeled but only reachable
for staff.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.permissions import DEALER_MANAGERS, DISTRIBUTOR_MANAGERS, ROLE_ADMIN, ROLE_DEALER, ROLE_DISTRIBUTOR, ROLE_FARMER, ROLE_SUPER_ADMIN
from app.models.models import DealerProductAvailability, DealerProfile, DistributorProfile, DistributorStock, FarmerSupportCase, User

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])

VALID_STATUSES = {"active", "suspended", "disabled"}


@router.get("/farmers")
def list_farmers(status: str | None = None, user: User = Depends(require_roles(ROLE_SUPER_ADMIN, ROLE_ADMIN)), db: Session = Depends(get_db)):
    query = db.query(User).filter(User.role == ROLE_FARMER)
    if status:
        query = query.filter(User.status == status)
    users = query.order_by(User.created_at.desc()).all()
    return [{"id": u.id, "email": u.email, "full_name": u.full_name, "status": u.status, "created_at": u.created_at.isoformat()} for u in users]


@router.post("/farmers/{user_id}/status/{new_status}")
def change_farmer_status(user_id: str, new_status: str, user: User = Depends(require_roles(ROLE_SUPER_ADMIN, ROLE_ADMIN)), db: Session = Depends(get_db)):
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status.")
    target = db.get(User, user_id)
    if not target or target.role != ROLE_FARMER:
        raise HTTPException(status_code=404, detail="Farmer account not found.")
    target.status = new_status
    record_audit(db, actor_id=user.id, action="farmer.status_change", entity_type="user", entity_id=target.id,
                 summary=f"Farmer account {target.email} -> {new_status}")
    db.commit()
    return {"ok": True}


@router.get("/dealers")
def list_dealer_accounts(status: str | None = None, user: User = Depends(require_roles(*DEALER_MANAGERS)), db: Session = Depends(get_db)):
    query = db.query(User).filter(User.role == ROLE_DEALER)
    if status:
        query = query.filter(User.status == status)
    users = query.order_by(User.created_at.desc()).all()
    return [{"id": u.id, "email": u.email, "full_name": u.full_name, "status": u.status, "created_at": u.created_at.isoformat()} for u in users]


@router.post("/dealers/{user_id}/status/{new_status}")
def change_dealer_status(user_id: str, new_status: str, user: User = Depends(require_roles(*DEALER_MANAGERS)), db: Session = Depends(get_db)):
    """Suspending a dealer's account also flips their profile's `suspended`
    flag, so they immediately drop out of the public directory and the
    farmer-case matching pool - the two states were previously able to
    drift apart (account suspended but still matched/listed)."""
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status.")
    target = db.get(User, user_id)
    if not target or target.role != ROLE_DEALER:
        raise HTTPException(status_code=404, detail="Dealer account not found.")
    target.status = new_status
    profile = db.query(DealerProfile).filter(DealerProfile.user_id == target.id).first()
    if profile:
        profile.suspended = new_status != "active"
    record_audit(db, actor_id=user.id, action="dealer.status_change", entity_type="user", entity_id=target.id,
                 summary=f"Dealer account {target.email} -> {new_status}")
    db.commit()
    return {"ok": True}


@router.delete("/dealers/{user_id}")
def delete_dealer(user_id: str, user: User = Depends(require_roles(ROLE_SUPER_ADMIN)), db: Session = Depends(get_db)):
    """Permanently removes the dealer's business profile - this is the
    genuine "make them stop appearing everywhere" action, distinct from
    Suspend (reversible, keeps the profile). The login account itself is
    disabled rather than deleted: dozens of tables reference users.id for
    audit/attribution (created_by_id, actor_id, etc.), and hard-deleting
    the row would either violate one of those foreign keys or silently
    erase that history - disabling achieves the same "can never log in
    again" outcome without either problem."""
    target = db.get(User, user_id)
    if not target or target.role != ROLE_DEALER:
        raise HTTPException(status_code=404, detail="Dealer account not found.")
    profile = db.query(DealerProfile).filter(DealerProfile.user_id == target.id).first()
    if profile:
        db.query(FarmerSupportCase).filter(FarmerSupportCase.assigned_dealer_id == profile.id).update({"assigned_dealer_id": None})
        db.query(DealerProductAvailability).filter(DealerProductAvailability.dealer_id == profile.id).delete()
        db.delete(profile)  # service_areas cascade via the ORM relationship
    target.status = "disabled"
    record_audit(db, actor_id=user.id, action="dealer.delete", entity_type="user", entity_id=target.id,
                 summary=f"Permanently deleted dealer profile and disabled account: {target.email}")
    db.commit()
    return {"ok": True}


@router.get("/distributors")
def list_distributor_accounts(status: str | None = None, user: User = Depends(require_roles(*DISTRIBUTOR_MANAGERS)), db: Session = Depends(get_db)):
    query = db.query(User).filter(User.role == ROLE_DISTRIBUTOR)
    if status:
        query = query.filter(User.status == status)
    users = query.order_by(User.created_at.desc()).all()
    return [{"id": u.id, "email": u.email, "full_name": u.full_name, "status": u.status, "created_at": u.created_at.isoformat()} for u in users]


@router.post("/distributors/{user_id}/status/{new_status}")
def change_distributor_status(user_id: str, new_status: str, user: User = Depends(require_roles(*DISTRIBUTOR_MANAGERS)), db: Session = Depends(get_db)):
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status.")
    target = db.get(User, user_id)
    if not target or target.role != ROLE_DISTRIBUTOR:
        raise HTTPException(status_code=404, detail="Distributor account not found.")
    target.status = new_status
    profile = db.query(DistributorProfile).filter(DistributorProfile.user_id == target.id).first()
    if profile:
        profile.suspended = new_status != "active"
    record_audit(db, actor_id=user.id, action="distributor.status_change", entity_type="user", entity_id=target.id,
                 summary=f"Distributor account {target.email} -> {new_status}")
    db.commit()
    return {"ok": True}


@router.delete("/distributors/{user_id}")
def delete_distributor(user_id: str, user: User = Depends(require_roles(ROLE_SUPER_ADMIN)), db: Session = Depends(get_db)):
    """Same reasoning as delete_dealer above - permanently removes the
    business profile, disables (doesn't delete) the login account."""
    target = db.get(User, user_id)
    if not target or target.role != ROLE_DISTRIBUTOR:
        raise HTTPException(status_code=404, detail="Distributor account not found.")
    profile = db.query(DistributorProfile).filter(DistributorProfile.user_id == target.id).first()
    if profile:
        db.query(DistributorStock).filter(DistributorStock.distributor_id == profile.id).delete()
        db.delete(profile)
    target.status = "disabled"
    record_audit(db, actor_id=user.id, action="distributor.delete", entity_type="user", entity_id=target.id,
                 summary=f"Permanently deleted distributor profile and disabled account: {target.email}")
    db.commit()
    return {"ok": True}
