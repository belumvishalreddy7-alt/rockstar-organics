import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles, require_user
from app.core.permissions import PRODUCT_CONTRIBUTORS, PRODUCT_MANAGERS, ROLE_DEALER
from app.models.models import Product, ProductReview, User
from app.schemas.schemas import ProductCreate, ProductStatusChange, ProductUpdate

router = APIRouter(prefix="/api/v1/products", tags=["products"])

VALID_TRANSITIONS = {
    "draft": {"in_review", "archived"},
    "in_review": {"approved", "rejected", "draft"},
    "approved": {"published", "draft"},
    "published": {"unpublished", "archived"},
    "unpublished": {"published", "archived"},
    "archived": {"draft"},
    "rejected": {"draft"},
}


def _empty_rating_summary() -> dict:
    return {"average_rating": None, "approved_review_count": 0, "rating_breakdown": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}}


def _rating_summaries(db: Session, product_ids: list[str]) -> dict[str, dict]:
    """One aggregate query for a whole page of products instead of one
    query per row - a page of `page_size=100` used to issue 100+ extra
    round trips here (plus one lazy `p.images` load per row), which
    matters once the database moves off a co-located instance to a
    networked one with real per-query latency. `rating_breakdown` is the
    1-5 star count distribution among approved reviews only - a pending/
    rejected/spam review never affects the public numbers."""
    summaries: dict[str, dict] = {pid: _empty_rating_summary() for pid in product_ids}
    if not product_ids:
        return summaries

    totals = (
        db.query(ProductReview.product_id, func.avg(ProductReview.rating), func.count(ProductReview.id))
        .filter(ProductReview.product_id.in_(product_ids), ProductReview.status == "approved")
        .group_by(ProductReview.product_id)
        .all()
    )
    for pid, avg, count in totals:
        summaries[pid]["average_rating"] = round(float(avg), 2) if avg else None
        summaries[pid]["approved_review_count"] = count or 0

    breakdown_rows = (
        db.query(ProductReview.product_id, ProductReview.rating, func.count(ProductReview.id))
        .filter(ProductReview.product_id.in_(product_ids), ProductReview.status == "approved")
        .group_by(ProductReview.product_id, ProductReview.rating)
        .all()
    )
    for pid, rating, count in breakdown_rows:
        if 1 <= rating <= 5:
            summaries[pid]["rating_breakdown"][str(rating)] = count or 0

    return summaries


def _serialize(p: Product, rating_summary: dict) -> dict:
    return {
        "id": p.id, "sku": p.sku, "name": p.name, "slug": p.slug, "category_id": p.category_id,
        "product_type": p.product_type, "short_description": p.short_description,
        "full_description": p.full_description, "benefits": p.benefits,
        "recommended_crops": p.recommended_crops, "crop_stage": p.crop_stage,
        "application_method": p.application_method, "dosage_value": p.dosage_value,
        "dosage_unit": p.dosage_unit, "pack_sizes": p.pack_sizes, "precautions": p.precautions,
        "regulatory_notes": p.regulatory_notes, "status": p.status, "featured": p.featured,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        "images": [{"id": i.id, "file_path": i.file_path, "alt_text": i.alt_text} for i in p.images],
        **rating_summary,
    }


@router.get("/public")
def public_catalogue(
    q: str | None = None,
    category_id: str | None = None,
    crop: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Product).options(joinedload(Product.images)).filter(Product.status == "published")
    if q:
        like = f"%{q}%"
        query = query.filter(Product.name.ilike(like) if hasattr(Product.name, "ilike") else Product.name.like(like))
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if crop:
        query = query.filter(Product.recommended_crops.like(f"%{crop}%"))
    total = query.count()
    items = query.order_by(Product.published_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    summaries = _rating_summaries(db, [p.id for p in items])
    return {"total": total, "page": page, "page_size": page_size, "items": [_serialize(p, summaries[p.id]) for p in items]}


@router.get("/public/{slug}")
def public_product_detail(slug: str, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.slug == slug, Product.status == "published").first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found.")
    out = _serialize(p, _rating_summaries(db, [p.id])[p.id])
    reviews = db.query(ProductReview).filter(ProductReview.product_id == p.id, ProductReview.status == "approved").order_by(ProductReview.created_at.desc()).all()
    out["reviews"] = [{"id": r.id, "reviewer_name": r.reviewer_name, "rating": r.rating, "comment": r.comment, "created_at": r.created_at.isoformat()} for r in reviews]
    return out


@router.get("")
def admin_list_products(status: str | None = None, page: int = 1, page_size: int = 20,
                         user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)),
                         db: Session = Depends(get_db)):
    query = db.query(Product).options(joinedload(Product.images))
    # A dealer only ever sees their own submitted listings, never other
    # dealers' or staff-created products - PRODUCT_CONTRIBUTORS lets a
    # dealer call this endpoint at all, but it must not become a way to
    # browse everyone else's unpublished drafts.
    if user.role == ROLE_DEALER:
        query = query.filter(Product.created_by_id == user.id)
    if status:
        query = query.filter(Product.status == status)
    total = query.count()
    items = query.order_by(Product.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    summaries = _rating_summaries(db, [p.id for p in items])
    return {"total": total, "items": [_serialize(p, summaries[p.id]) for p in items]}


@router.post("")
def create_product(payload: ProductCreate, user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)),
                    db: Session = Depends(get_db)):
    if db.query(Product).filter(Product.sku == payload.sku).first():
        raise HTTPException(status_code=400, detail="A product with this SKU already exists.")
    if db.query(Product).filter(Product.slug == payload.slug).first():
        raise HTTPException(status_code=400, detail="A product with this slug already exists.")
    p = Product(**payload.model_dump(), created_by_id=user.id, updated_by_id=user.id, status="draft")
    db.add(p)
    db.flush()
    record_audit(db, actor_id=user.id, action="product.create", entity_type="product", entity_id=p.id, summary=f"Created draft product {p.name}")
    db.commit()
    db.refresh(p)
    return _serialize(p, _rating_summaries(db, [p.id])[p.id])


@router.put("/{product_id}")
def update_product(product_id: str, payload: ProductUpdate, user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)),
                    db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found.")
    # A dealer may only edit their own listing, and only before it has
    # been submitted for staff review - once it moves to in_review or
    # beyond, further changes go through staff (PRODUCT_MANAGERS).
    if user.role == ROLE_DEALER:
        if p.created_by_id != user.id:
            raise HTTPException(status_code=403, detail="You can only edit your own product listings.")
        if p.status != "draft":
            raise HTTPException(status_code=400, detail="This listing has already been submitted and can no longer be edited directly.")
    for field, value in payload.model_dump().items():
        setattr(p, field, value)
    p.updated_by_id = user.id
    record_audit(db, actor_id=user.id, action="product.update", entity_type="product", entity_id=p.id, summary=f"Updated product {p.name}")
    db.commit()
    db.refresh(p)
    return _serialize(p, _rating_summaries(db, [p.id])[p.id])


@router.post("/{product_id}/transition/{new_status}")
def transition_product(product_id: str, new_status: str, payload: ProductStatusChange,
                        user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)),
                        db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found.")
    # A dealer's only allowed transition is submitting their own draft for
    # staff review - approving/publishing/archiving/rejecting stays with
    # PRODUCT_MANAGERS, same as the certificate/photo verification workflow.
    if user.role == ROLE_DEALER:
        if p.created_by_id != user.id or new_status != "in_review" or p.status != "draft":
            raise HTTPException(status_code=403, detail="Dealers may only submit their own draft listing for review.")
    allowed = VALID_TRANSITIONS.get(p.status, set())
    if new_status not in allowed:
        raise HTTPException(status_code=400, detail=f"Cannot move product from '{p.status}' to '{new_status}'.")

    if new_status == "published":
        missing = []
        if not p.category_id:
            missing.append("category")
        if not p.full_description:
            missing.append("full description")
        if not p.precautions:
            missing.append("precautions")
        if missing:
            raise HTTPException(status_code=400, detail=f"Cannot publish: missing {', '.join(missing)}.")
        p.published_at = dt.datetime.utcnow()

    if new_status == "rejected":
        p.rejection_reason = payload.reason

    if new_status == "in_review":
        p.reviewer_id = None
    if new_status == "approved":
        p.reviewer_id = user.id

    old_status = p.status
    p.status = new_status
    record_audit(db, actor_id=user.id, action=f"product.{new_status}", entity_type="product", entity_id=p.id,
                 summary=f"Product {p.name} moved from {old_status} to {new_status}")
    db.commit()
    db.refresh(p)
    return _serialize(p, _rating_summaries(db, [p.id])[p.id])


@router.delete("/{product_id}")
def delete_product(product_id: str, user: User = Depends(require_roles("super_admin")), db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found.")
    record_audit(db, actor_id=user.id, action="product.delete", entity_type="product", entity_id=p.id, summary=f"Permanently deleted product {p.name}")
    db.delete(p)
    db.commit()
    return {"ok": True}
