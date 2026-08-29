"""Farmer self-service profile - the farm information (district, crops,
irrigation, etc.) collected at registration but never previously exposed
for a farmer to view or update themselves, matching the same
GET/PUT-me/profile pattern already used by dealers.py and distributors.py."""
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.permissions import ROLE_FARMER
from app.models.models import FarmerProfile, User
from app.schemas.schemas import FarmerProfileUpdate

router = APIRouter(prefix="/api/v1/farmers", tags=["farmers"])


def _serialize(profile: FarmerProfile) -> dict:
    return {
        "id": profile.id, "state": profile.state, "district": profile.district, "mandal": profile.mandal,
        "village": profile.village, "pin_code": profile.pin_code,
        "farm_size": float(profile.farm_size) if profile.farm_size is not None else None,
        "farm_size_unit": profile.farm_size_unit, "main_crops": profile.main_crops,
        "irrigation_type": profile.irrigation_type, "preferred_language": profile.preferred_language,
        "preferred_contact_method": profile.preferred_contact_method, "public_data_opt_in": profile.public_data_opt_in,
    }


@router.get("/me/profile")
def my_farmer_profile(user: User = Depends(require_roles(ROLE_FARMER)), db: Session = Depends(get_db)):
    profile = db.query(FarmerProfile).filter(FarmerProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Farmer profile not found.")
    return _serialize(profile)


@router.put("/me/profile")
def update_my_farmer_profile(payload: FarmerProfileUpdate, user: User = Depends(require_roles(ROLE_FARMER)), db: Session = Depends(get_db)):
    profile = db.query(FarmerProfile).filter(FarmerProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Farmer profile not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    record_audit(db, actor_id=user.id, action="farmer.profile_update", entity_type="farmer_profile", entity_id=profile.id,
                 summary="Farmer updated their profile")
    db.commit()
    db.refresh(profile)
    return _serialize(profile)
