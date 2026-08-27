from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.permissions import SETTINGS_MANAGERS
from app.models.models import CompanySetting, User
from app.schemas.schemas import CompanySettingUpdate

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

# Required company setting keys, seeded empty. See section 5 of the spec:
# only status/role/site-content keys may be seeded, never fake business data.
REQUIRED_KEYS = [
    "company_name", "tagline", "support_email", "sales_email", "phone", "whatsapp_number",
    "address", "district", "state", "pin_code", "service_areas", "business_hours",
    "default_seo_title", "default_seo_description", "footer_text", "maintenance_mode",
    "farmer_registration_enabled", "map_link",
]


@router.get("/public")
def public_settings(db: Session = Depends(get_db)):
    rows = db.query(CompanySetting).filter(CompanySetting.key.in_(REQUIRED_KEYS)).all()
    return {r.key: r.value for r in rows}


@router.get("")
def all_settings(user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
    rows = db.query(CompanySetting).all()
    return {r.key: r.value for r in rows}


@router.put("")
def update_setting(payload: CompanySettingUpdate, user: User = Depends(require_roles(*SETTINGS_MANAGERS)), db: Session = Depends(get_db)):
    row = db.get(CompanySetting, payload.key)
    if not row:
        row = CompanySetting(key=payload.key)
        db.add(row)
    row.value = payload.value
    row.updated_by_id = user.id
    record_audit(db, actor_id=user.id, action="settings.update", entity_type="company_setting", entity_id=payload.key,
                 summary=f"Setting '{payload.key}' updated")
    db.commit()
    return {"ok": True}
