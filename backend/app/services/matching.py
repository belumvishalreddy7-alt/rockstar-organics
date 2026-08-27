"""
Transparent dealer matching for farmer support cases.

This is a scoring rule, not a hidden algorithm: every point is explained in
the `reasons` list returned for each candidate so staff can see exactly why
a dealer was suggested.
"""
from sqlalchemy.orm import Session

from app.models.models import DealerProfile, DealerServiceArea


def find_matching_dealers(db: Session, *, district: str, mandal: str | None) -> list[dict]:
    dealers = (
        db.query(DealerProfile)
        .filter(DealerProfile.farmer_case_opt_in == True, DealerProfile.suspended == False)  # noqa: E712
        .all()
    )
    results = []
    for d in dealers:
        areas = db.query(DealerServiceArea).filter(DealerServiceArea.dealer_id == d.id).all()
        district_match = any(a.district == district for a in areas)
        mandal_match = bool(mandal) and any(a.district == district and a.mandal == mandal for a in areas)
        if not district_match:
            continue
        score = 0
        reasons = []
        if district_match:
            score += 40
            reasons.append("Dealer services this district.")
        if mandal_match:
            score += 30
            reasons.append("Dealer services this exact mandal.")
        if d.last_activity_at:
            score += 10
            reasons.append("Dealer has a recorded activity/availability confirmation.")
        results.append({
            "dealer_id": d.id,
            "business_name": d.business_name,
            "score": score,
            "reasons": reasons,
            "district_match": district_match,
            "mandal_match": mandal_match,
            "last_activity_at": d.last_activity_at.isoformat() if d.last_activity_at else None,
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    return results
