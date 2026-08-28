import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles, require_user
from app.core.permissions import STAFF_ROLES
from app.models.models import FollowUpTask, User
from app.schemas.schemas import FollowUpTaskCreate

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def _serialize(t: FollowUpTask) -> dict:
    return {"id": t.id, "title": t.title, "description": t.description, "related_entity_type": t.related_entity_type,
            "related_entity_id": t.related_entity_id, "assigned_user_id": t.assigned_user_id, "priority": t.priority,
            "due_date": t.due_date.isoformat() if t.due_date else None, "status": t.status,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "created_at": t.created_at.isoformat(), "overdue": bool(t.due_date and t.due_date < dt.datetime.utcnow() and t.status in ("open", "in_progress"))}


@router.get("")
def list_tasks(status: str | None = None, mine_only: bool = False,
               user: User = Depends(require_roles(*STAFF_ROLES)), db: Session = Depends(get_db)):
    query = db.query(FollowUpTask)
    if status:
        query = query.filter(FollowUpTask.status == status)
    if mine_only:
        query = query.filter(FollowUpTask.assigned_user_id == user.id)
    from sqlalchemy import nulls_last
    items = query.order_by(nulls_last(FollowUpTask.due_date.asc()), FollowUpTask.created_at.desc()).all()
    return [_serialize(t) for t in items]


@router.post("")
def create_task(payload: FollowUpTaskCreate, user: User = Depends(require_roles(*STAFF_ROLES)), db: Session = Depends(get_db)):
    t = FollowUpTask(**payload.model_dump(), created_by_id=user.id, status="open")
    db.add(t)
    db.flush()
    record_audit(db, actor_id=user.id, action="task.create", entity_type="follow_up_task", entity_id=t.id, summary=f"Task created: {t.title}")
    db.commit()
    db.refresh(t)
    return _serialize(t)


@router.post("/{task_id}/status/{new_status}")
def change_task_status(task_id: str, new_status: str, user: User = Depends(require_roles(*STAFF_ROLES)), db: Session = Depends(get_db)):
    if new_status not in {"open", "in_progress", "blocked", "completed", "cancelled"}:
        raise HTTPException(status_code=400, detail="Invalid status.")
    t = db.get(FollowUpTask, task_id)
    if not t:
        raise HTTPException(status_code=404, detail="Task not found.")
    t.status = new_status
    if new_status == "completed":
        t.completed_at = dt.datetime.utcnow()
    record_audit(db, actor_id=user.id, action="task.status_change", entity_type="follow_up_task", entity_id=t.id,
                 summary=f"Task {t.title} -> {new_status}")
    db.commit()
    return {"ok": True}


@router.post("/{task_id}/assign/{assignee_id}")
def assign_task(task_id: str, assignee_id: str, user: User = Depends(require_roles(*STAFF_ROLES)), db: Session = Depends(get_db)):
    t = db.get(FollowUpTask, task_id)
    if not t:
        raise HTTPException(status_code=404, detail="Task not found.")
    if not db.get(User, assignee_id):
        raise HTTPException(status_code=404, detail="Assignee not found.")
    t.assigned_user_id = assignee_id
    record_audit(db, actor_id=user.id, action="task.assign", entity_type="follow_up_task", entity_id=t.id, summary=f"Task {t.title} reassigned")
    db.commit()
    return {"ok": True}
