import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles, require_user
from app.core.notify import notify
from app.core.permissions import CASE_MANAGERS, ROLE_DEALER, ROLE_FARMER
from app.core.references import generate_reference
from app.models.models import CaseMessage, DealerProfile, FarmerSupportCase, User
from app.schemas.schemas import CaseAssignRequest, CaseMessageCreate, CaseStatusChange, SupportCaseCreate
from app.services.matching import find_matching_dealers

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])

VALID_STATUSES = {
    "new", "triage", "waiting_for_assignment", "assigned_to_dealer", "assigned_to_field_officer",
    "in_progress", "waiting_for_farmer", "visit_requested", "visit_scheduled", "under_review",
    "resolved", "closed", "spam", "cancelled",
}


def _timeline_entry(db: Session, case_id: str, author_id: str | None, body: str, event_type: str, is_private: bool = False):
    db.add(CaseMessage(case_id=case_id, author_id=author_id, body=body, event_type=event_type, is_private=is_private))


@router.post("")
def create_case(payload: SupportCaseCreate, user: User = Depends(require_roles(ROLE_FARMER)), db: Session = Depends(get_db)):
    case = FarmerSupportCase(
        **payload.model_dump(), reference_number=generate_reference("CASE"), farmer_id=user.id, status="new",
    )
    db.add(case)
    db.flush()
    _timeline_entry(db, case.id, user.id, "Case submitted by farmer.", "status_change")
    record_audit(db, actor_id=user.id, action="case.create", entity_type="farmer_support_case", entity_id=case.id,
                 summary=f"Farmer case {case.reference_number} submitted")
    db.commit()
    db.refresh(case)
    return {"id": case.id, "reference_number": case.reference_number, "status": case.status}


@router.get("/mine")
def my_cases(user: User = Depends(require_roles(ROLE_FARMER)), db: Session = Depends(get_db)):
    cases = db.query(FarmerSupportCase).filter(FarmerSupportCase.farmer_id == user.id).order_by(FarmerSupportCase.created_at.desc()).all()
    return [{"id": c.id, "reference_number": c.reference_number, "title": c.title, "status": c.status, "created_at": c.created_at.isoformat()} for c in cases]


@router.get("")
def list_cases(status: str | None = None, district: str | None = None,
               user: User = Depends(require_roles(*CASE_MANAGERS)), db: Session = Depends(get_db)):
    query = db.query(FarmerSupportCase)
    if status:
        query = query.filter(FarmerSupportCase.status == status)
    if district:
        query = query.filter(FarmerSupportCase.district == district)
    cases = query.order_by(FarmerSupportCase.created_at.desc()).all()
    return [{"id": c.id, "reference_number": c.reference_number, "title": c.title, "status": c.status,
             "district": c.district, "priority": c.priority, "severity": c.severity} for c in cases]


def _get_case_for_viewer(db: Session, case_id: str, user: User) -> FarmerSupportCase:
    case = db.get(FarmerSupportCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    if user.role == ROLE_FARMER and case.farmer_id != user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this case.")
    if user.role == ROLE_DEALER:
        profile = db.query(DealerProfile).filter(DealerProfile.user_id == user.id).first()
        if not profile or case.assigned_dealer_id != profile.id:
            raise HTTPException(status_code=403, detail="You do not have access to this case.")
    return case


@router.get("/{case_id}")
def get_case(case_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    case = _get_case_for_viewer(db, case_id, user)
    messages_query = db.query(CaseMessage).filter(CaseMessage.case_id == case.id)
    if user.role in (ROLE_FARMER,):
        messages_query = messages_query.filter(CaseMessage.is_private == False)  # noqa: E712
    messages = messages_query.order_by(CaseMessage.created_at.asc()).all()
    return {
        "id": case.id, "reference_number": case.reference_number, "title": case.title, "description": case.description,
        "status": case.status, "district": case.district, "mandal": case.mandal, "severity": case.severity,
        "priority": case.priority, "assigned_dealer_id": case.assigned_dealer_id,
        "assigned_field_officer_id": case.assigned_field_officer_id,
        "timeline": [{"id": m.id, "body": m.body, "is_private": m.is_private, "event_type": m.event_type,
                      "created_at": m.created_at.isoformat()} for m in messages],
    }


@router.get("/{case_id}/matches")
def get_matches(case_id: str, user: User = Depends(require_roles(*CASE_MANAGERS)), db: Session = Depends(get_db)):
    case = db.get(FarmerSupportCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return find_matching_dealers(db, district=case.district, mandal=case.mandal)


@router.post("/{case_id}/assign")
def assign_case(case_id: str, payload: CaseAssignRequest, user: User = Depends(require_roles(*CASE_MANAGERS)), db: Session = Depends(get_db)):
    case = db.get(FarmerSupportCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    parts = []
    if payload.dealer_id is not None:
        case.assigned_dealer_id = payload.dealer_id
        case.status = "assigned_to_dealer"
        parts.append("dealer")
        dealer = db.get(DealerProfile, payload.dealer_id)
        if dealer:
            notify(db, recipient_id=dealer.user_id, type="case_assigned", title="New farmer case assigned",
                   message=f"Case {case.reference_number} has been assigned to you.", related_entity_type="farmer_support_case", related_entity_id=case.id)
    if payload.field_officer_id is not None:
        case.assigned_field_officer_id = payload.field_officer_id
        case.status = "assigned_to_field_officer"
        parts.append("field officer")
        notify(db, recipient_id=payload.field_officer_id, type="case_assigned", title="New farmer case assigned",
               message=f"Case {case.reference_number} has been assigned to you.", related_entity_type="farmer_support_case", related_entity_id=case.id)
    if payload.staff_id is not None:
        case.assigned_staff_id = payload.staff_id
        parts.append("staff member")

    _timeline_entry(db, case.id, user.id, f"Case assigned to {', '.join(parts) or 'no one'}.", "assignment")
    record_audit(db, actor_id=user.id, action="case.assign", entity_type="farmer_support_case", entity_id=case.id,
                 summary=f"Case {case.reference_number} assigned ({', '.join(parts)})")
    db.commit()
    return {"ok": True}


@router.post("/{case_id}/status")
def change_status(case_id: str, payload: CaseStatusChange, user: User = Depends(require_user), db: Session = Depends(get_db)):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status.")
    case = _get_case_for_viewer(db, case_id, user)
    if user.role == ROLE_FARMER and payload.status not in ("cancelled",):
        raise HTTPException(status_code=403, detail="Farmers may only cancel their own case.")

    old_status = case.status
    case.status = payload.status
    if payload.status in ("resolved", "closed"):
        case.resolved_at = dt.datetime.utcnow()
        case.closure_reason = payload.note
    _timeline_entry(db, case.id, user.id, payload.note or f"Status changed from {old_status} to {payload.status}.", "status_change")
    record_audit(db, actor_id=user.id, action="case.status_change", entity_type="farmer_support_case", entity_id=case.id,
                 summary=f"Case {case.reference_number}: {old_status} -> {payload.status}")
    if case.farmer_id != user.id:
        notify(db, recipient_id=case.farmer_id, type="case_status_changed", title="Your support case was updated",
               message=f"Case {case.reference_number} is now {payload.status.replace('_', ' ')}.",
               related_entity_type="farmer_support_case", related_entity_id=case.id)
    db.commit()
    return {"ok": True}


@router.post("/{case_id}/messages")
def add_message(case_id: str, payload: CaseMessageCreate, user: User = Depends(require_user), db: Session = Depends(get_db)):
    case = _get_case_for_viewer(db, case_id, user)
    is_private = payload.is_private and user.role != "farmer"
    _timeline_entry(db, case.id, user.id, payload.body, "message", is_private=is_private)
    if not is_private and case.farmer_id != user.id:
        notify(db, recipient_id=case.farmer_id, type="case_response", title="New message on your case",
               message=f"There is a new response on case {case.reference_number}.",
               related_entity_type="farmer_support_case", related_entity_id=case.id)
    db.commit()
    return {"ok": True}
