from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles, require_user
from app.core.notify import notify
from app.core.permissions import CASE_MANAGERS, ROLE_FARMER, ROLE_FIELD_OFFICER
from app.core.references import generate_reference
from app.models.models import FarmerSupportCase, FieldVisit, FollowUpTask, User
from app.schemas.schemas import FieldVisitComplete, FieldVisitCreate, FieldVisitSchedule

router = APIRouter(prefix="/api/v1/visits", tags=["visits"])


@router.post("")
def request_visit(payload: FieldVisitCreate, user: User = Depends(require_roles(ROLE_FARMER)), db: Session = Depends(get_db)):
    case = db.get(FarmerSupportCase, payload.case_id)
    if not case or case.farmer_id != user.id:
        raise HTTPException(status_code=404, detail="Case not found.")
    visit = FieldVisit(
        reference_number=generate_reference("VISIT"), case_id=case.id, farmer_id=user.id, status="requested",
        requested_date=payload.requested_date, purpose=payload.purpose, farmer_instructions=payload.farmer_instructions,
    )
    db.add(visit)
    case.status = "visit_requested"
    record_audit(db, actor_id=user.id, action="visit.request", entity_type="field_visit", entity_id=visit.id,
                 summary=f"Field visit requested for case {case.reference_number}")
    db.commit()
    db.refresh(visit)
    return {"id": visit.id, "reference_number": visit.reference_number, "status": visit.status}


@router.get("")
def list_visits(status: str | None = None, user: User = Depends(require_roles(*CASE_MANAGERS)), db: Session = Depends(get_db)):
    query = db.query(FieldVisit)
    if status:
        query = query.filter(FieldVisit.status == status)
    visits = query.order_by(FieldVisit.created_at.desc()).all()
    return [{"id": v.id, "reference_number": v.reference_number, "status": v.status,
             "scheduled_start": v.scheduled_start.isoformat() if v.scheduled_start else None} for v in visits]


@router.get("/mine")
def my_visits(user: User = Depends(require_roles(ROLE_FARMER)), db: Session = Depends(get_db)):
    visits = db.query(FieldVisit).filter(FieldVisit.farmer_id == user.id).order_by(FieldVisit.created_at.desc()).all()
    return [{"id": v.id, "reference_number": v.reference_number, "status": v.status,
             "scheduled_start": v.scheduled_start.isoformat() if v.scheduled_start else None} for v in visits]


@router.get("/assigned-to-me")
def my_assigned_visits(status: str | None = None, user: User = Depends(require_roles(ROLE_FIELD_OFFICER, *CASE_MANAGERS)),
                        db: Session = Depends(get_db)):
    """A field officer's own dashboard view - unlike list_visits (every
    visit, staff-wide), this is scoped to visits assigned specifically to
    the caller, so a field officer sees their own schedule rather than
    everyone's."""
    query = db.query(FieldVisit).filter(FieldVisit.assigned_officer_id == user.id)
    if status:
        query = query.filter(FieldVisit.status == status)
    visits = query.order_by(FieldVisit.scheduled_start.asc().nulls_last()).all()
    out = []
    for v in visits:
        case = db.get(FarmerSupportCase, v.case_id)
        farmer = db.get(User, v.farmer_id)
        out.append({
            "id": v.id, "reference_number": v.reference_number, "status": v.status,
            "purpose": v.purpose, "scheduled_start": v.scheduled_start.isoformat() if v.scheduled_start else None,
            "scheduled_end": v.scheduled_end.isoformat() if v.scheduled_end else None,
            "internal_instructions": v.internal_instructions, "farmer_instructions": v.farmer_instructions,
            "follow_up_required": v.follow_up_required,
            "case_reference": case.reference_number if case else None,
            "case_title": case.title if case else None,
            "farmer_name": farmer.full_name if farmer else None,
        })
    return out


@router.post("/{visit_id}/schedule")
def schedule_visit(visit_id: str, payload: FieldVisitSchedule, user: User = Depends(require_roles(*CASE_MANAGERS)), db: Session = Depends(get_db)):
    visit = db.get(FieldVisit, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found.")
    if payload.scheduled_end <= payload.scheduled_start:
        raise HTTPException(status_code=400, detail="Visit end time must be after start time.")

    conflict = (
        db.query(FieldVisit)
        .filter(FieldVisit.assigned_officer_id == payload.assigned_officer_id, FieldVisit.id != visit.id,
                FieldVisit.status.in_(["scheduled", "confirmed"]),
                FieldVisit.scheduled_start < payload.scheduled_end, FieldVisit.scheduled_end > payload.scheduled_start)
        .first()
    )
    if conflict:
        raise HTTPException(status_code=409, detail="This field officer already has a visit scheduled in that time window.")

    visit.assigned_officer_id = payload.assigned_officer_id
    visit.scheduled_start = payload.scheduled_start
    visit.scheduled_end = payload.scheduled_end
    visit.internal_instructions = payload.internal_instructions
    visit.status = "scheduled"
    case = db.get(FarmerSupportCase, visit.case_id)
    if case:
        case.status = "visit_scheduled"
    notify(db, recipient_id=visit.farmer_id, type="visit_scheduled", title="Field visit scheduled",
           message=f"Your field visit {visit.reference_number} has been scheduled.", related_entity_type="field_visit", related_entity_id=visit.id)
    notify(db, recipient_id=payload.assigned_officer_id, type="visit_scheduled", title="Field visit assigned to you",
           message=f"Visit {visit.reference_number} has been scheduled to you.", related_entity_type="field_visit", related_entity_id=visit.id)
    record_audit(db, actor_id=user.id, action="visit.schedule", entity_type="field_visit", entity_id=visit.id,
                 summary=f"Visit {visit.reference_number} scheduled")
    db.commit()
    return {"ok": True}


@router.post("/{visit_id}/complete")
def complete_visit(visit_id: str, payload: FieldVisitComplete, user: User = Depends(require_roles(*CASE_MANAGERS)), db: Session = Depends(get_db)):
    visit = db.get(FieldVisit, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found.")
    visit.status = "completed"
    visit.visit_summary = payload.visit_summary
    visit.follow_up_required = payload.follow_up_required
    case = db.get(FarmerSupportCase, visit.case_id)
    if case:
        case.status = "under_review"
    if payload.follow_up_required:
        db.add(FollowUpTask(title=f"Follow up on visit {visit.reference_number}", description=payload.visit_summary,
                             related_entity_type="field_visit", related_entity_id=visit.id, assigned_user_id=visit.assigned_officer_id,
                             created_by_id=user.id, priority="normal"))
    record_audit(db, actor_id=user.id, action="visit.complete", entity_type="field_visit", entity_id=visit.id,
                 summary=f"Visit {visit.reference_number} completed")
    db.commit()
    return {"ok": True}
