from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.permissions import REVIEW_MODERATORS
from app.core.rate_limit import rate_limiter
from app.models.models import Product, ProductReview, User
from app.schemas.schemas import ReviewCreate, ReviewModeration

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])
settings = get_settings()


@router.post("/products/{product_id}")
def submit_review(product_id: str, payload: ReviewCreate, request: Request, user: User | None = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product or product.status != "published":
        raise HTTPException(status_code=400, detail="Reviews can only be submitted for published products.")

    # Keyed by IP (not just the client-supplied reviewer_name, which is
    # trivially spoofable) so an anonymous submitter can't bypass the limit
    # by just typing a different name each time.
    ip = request.client.host if request.client else "unknown"
    limiter_key = f"review:{user.id if user else ip}:{product_id}"
    if not rate_limiter.check(limiter_key, 3, 3600):
        raise HTTPException(status_code=429, detail="Too many review submissions. Please try again later.")

    duplicate = None
    if user:
        duplicate = db.query(ProductReview).filter(ProductReview.product_id == product_id, ProductReview.user_id == user.id).first()
    if duplicate:
        raise HTTPException(status_code=400, detail="You have already submitted a review for this product.")

    review = ProductReview(product_id=product_id, user_id=user.id if user else None, reviewer_name=payload.reviewer_name,
                            rating=payload.rating, comment=payload.comment, status="pending")
    db.add(review)
    db.flush()
    record_audit(db, actor_id=user.id if user else None, action="review.submit", entity_type="product_review", entity_id=review.id,
                 summary=f"Review submitted for product {product.name}")
    db.commit()
    return {"ok": True, "status": "pending"}


@router.get("/pending")
def pending_reviews(user: User = Depends(require_roles(*REVIEW_MODERATORS)), db: Session = Depends(get_db)):
    reviews = db.query(ProductReview).filter(ProductReview.status == "pending").order_by(ProductReview.created_at.asc()).all()
    return [{"id": r.id, "product_id": r.product_id, "reviewer_name": r.reviewer_name, "rating": r.rating, "comment": r.comment,
             "created_at": r.created_at.isoformat()} for r in reviews]


@router.post("/{review_id}/moderate")
def moderate_review(review_id: str, payload: ReviewModeration, user: User = Depends(require_roles(*REVIEW_MODERATORS)), db: Session = Depends(get_db)):
    import datetime as dt
    if payload.status not in {"approved", "rejected", "spam"}:
        raise HTTPException(status_code=400, detail="Invalid moderation status.")
    r = db.get(ProductReview, review_id)
    if not r:
        raise HTTPException(status_code=404, detail="Review not found.")
    r.status = payload.status
    r.moderator_id = user.id
    r.moderator_notes = payload.moderator_notes
    r.moderated_at = dt.datetime.utcnow()
    record_audit(db, actor_id=user.id, action="review.moderate", entity_type="product_review", entity_id=r.id, summary=f"Review moderated: {payload.status}")
    db.commit()
    return {"ok": True}
