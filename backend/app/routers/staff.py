"""Staff account management, restricted to Super Administrator / Administrator.
Staff accounts are never self-registered; see spec section 7."""
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.notify import notify
from app.core.permissions import ROLE_ADMIN, ROLE_SUPER_ADMIN, STAFF_ROLES
from app.core.security import hash_password
from app.models.models import User

router = APIRouter(prefix="/api/v1/staff", tags=["staff"])


@router.get("")
def list_staff(user: User = Depends(require_roles(ROLE_SUPER_ADMIN, ROLE_ADMIN)), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.role.in_(STAFF_ROLES)).all()
    return [{"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role, "status": u.status} for u in users]


@router.post("/invite")
def invite_staff(email: str, full_name: str, role: str, user: User = Depends(require_roles(ROLE_SUPER_ADMIN, ROLE_ADMIN)), db: Session = Depends(get_db)):
    if role not in STAFF_ROLES:
        raise HTTPException(status_code=400, detail="Invalid staff role.")
    if role == "super_admin" and user.role != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only a Super Administrator can create another Super Administrator.")
    if db.query(User).filter(User.email == email.lower()).first():
        raise HTTPException(status_code=400, detail="A user with this email already exists.")

    temp_password = secrets.token_urlsafe(9)
    staff_user = User(email=email.lower(), password_hash=hash_password(temp_password), role=role, full_name=full_name,
                       status="active", must_change_password=True)
    db.add(staff_user)
    db.flush()
    notify(db, recipient_id=staff_user.id, type="staff_invited", title="Welcome to Rockstar Organics",
           message="Your staff account has been created. Sign in and change your temporary password.")
    record_audit(db, actor_id=user.id, action="staff.invite", entity_type="user", entity_id=staff_user.id,
                 summary=f"Staff account created: {staff_user.email} ({role})")
    db.commit()
    return {"email": staff_user.email, "temporary_password": temp_password}


@router.post("/{user_id}/status/{new_status}")
def change_status(user_id: str, new_status: str, user: User = Depends(require_roles(ROLE_SUPER_ADMIN, ROLE_ADMIN)), db: Session = Depends(get_db)):
    if new_status not in {"active", "suspended", "disabled"}:
        raise HTTPException(status_code=400, detail="Invalid status.")
    target = db.get(User, user_id)
    if not target or target.role not in STAFF_ROLES:
        raise HTTPException(status_code=404, detail="Staff account not found.")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="You cannot change your own account status.")
    target.status = new_status
    record_audit(db, actor_id=user.id, action="staff.status_change", entity_type="user", entity_id=target.id,
                 summary=f"Staff account {target.email} -> {new_status}")
    db.commit()
    return {"ok": True}
