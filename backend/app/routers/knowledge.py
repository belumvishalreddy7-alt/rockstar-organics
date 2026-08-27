import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.permissions import PRODUCT_MANAGERS
from app.models.models import KnowledgeArticle, User
from app.schemas.schemas import KnowledgeArticleCreate

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

# Draft -> In Review -> Approved -> Published; Archived/Rejected as terminal-ish states.
VALID_TRANSITIONS = {
    "draft": {"in_review", "archived"},
    "in_review": {"approved", "rejected", "draft"},
    "approved": {"published", "draft"},
    "published": {"archived"},
    "archived": {"draft"},
    "rejected": {"draft"},
}


def _serialize(a: KnowledgeArticle) -> dict:
    return {"id": a.id, "title": a.title, "slug": a.slug, "summary": a.summary, "body": a.body, "topic": a.topic,
            "crops": a.crops, "region": a.region, "status": a.status, "disclaimer": a.disclaimer,
            "published_date": a.published_date.isoformat() if a.published_date else None,
            "last_reviewed_date": a.last_reviewed_date.isoformat() if a.last_reviewed_date else None}


@router.get("/public")
def public_articles(db: Session = Depends(get_db)):
    items = db.query(KnowledgeArticle).filter(KnowledgeArticle.status == "published").order_by(KnowledgeArticle.published_date.desc()).all()
    return [_serialize(a) for a in items]


@router.get("/public/{slug}")
def public_article_detail(slug: str, db: Session = Depends(get_db)):
    a = db.query(KnowledgeArticle).filter(KnowledgeArticle.slug == slug, KnowledgeArticle.status == "published").first()
    if not a:
        raise HTTPException(status_code=404, detail="Article not found.")
    return _serialize(a)


@router.get("")
def list_articles(status: str | None = None, user: User = Depends(require_roles(*PRODUCT_MANAGERS, "super_admin")), db: Session = Depends(get_db)):
    query = db.query(KnowledgeArticle)
    if status:
        query = query.filter(KnowledgeArticle.status == status)
    return [_serialize(a) for a in query.order_by(KnowledgeArticle.updated_at.desc()).all()]


@router.post("")
def create_article(payload: KnowledgeArticleCreate, user: User = Depends(require_roles(*PRODUCT_MANAGERS, "super_admin")), db: Session = Depends(get_db)):
    if db.query(KnowledgeArticle).filter(KnowledgeArticle.slug == payload.slug).first():
        raise HTTPException(status_code=400, detail="An article with this slug already exists.")
    a = KnowledgeArticle(**payload.model_dump(), status="draft", author_id=user.id)
    db.add(a)
    db.flush()
    record_audit(db, actor_id=user.id, action="knowledge.create", entity_type="knowledge_article", entity_id=a.id,
                 summary=f"Created draft article {a.title}")
    db.commit()
    db.refresh(a)
    return _serialize(a)


@router.post("/{article_id}/transition/{new_status}")
def transition_article(article_id: str, new_status: str, user: User = Depends(require_roles(*PRODUCT_MANAGERS, "super_admin")),
                        db: Session = Depends(get_db)):
    a = db.get(KnowledgeArticle, article_id)
    if not a:
        raise HTTPException(status_code=404, detail="Article not found.")
    allowed = VALID_TRANSITIONS.get(a.status, set())
    if new_status not in allowed:
        raise HTTPException(status_code=400, detail=f"Cannot move article from '{a.status}' to '{new_status}'.")

    if new_status == "published" and a.status != "approved":
        raise HTTPException(status_code=400, detail="An article must be approved by a reviewer before publication.")
    if new_status == "approved":
        a.reviewer_id = user.id
        a.last_reviewed_date = dt.datetime.utcnow()
    if new_status == "published":
        a.published_date = dt.datetime.utcnow()

    old = a.status
    a.status = new_status
    record_audit(db, actor_id=user.id, action=f"knowledge.{new_status}", entity_type="knowledge_article", entity_id=a.id,
                 summary=f"Article {a.title} moved from {old} to {new_status}")
    db.commit()
    db.refresh(a)
    return _serialize(a)
