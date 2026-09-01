import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles, require_user
from app.core.permissions import CONTENT_VERIFIERS, PRODUCT_CONTRIBUTORS, PRODUCT_MANAGERS, SETTINGS_MANAGERS
from app.models.models import (
    Product,
    ProductCertification,
    ProductClaim,
    ProductCrop,
    ProductDocument,
    ProductImage,
    ProductPackSize,
    ProductReview,
    User,
)
from app.schemas.schemas import (
    ProductCertificationCreate,
    ProductClaimCreate,
    ProductCreate,
    ProductCropCreate,
    ProductDocumentCreate,
    ProductPackSizeCreate,
    ProductStatusChange,
    ProductUpdate,
    VerificationStatusChange,
)

router = APIRouter(prefix="/api/v1/products", tags=["products"])

# Every (from_status, to_status) pair the workflow allows, mapped to the role
# set required to make that specific move. draft->in_review is kept as a
# direct path (not just draft->pending_verification->in_review) so every
# product created before 2026-08-28 and every existing test keeps working -
# pending_verification/revision_required are an additional, fuller path,
# not a replacement of the original shorter one.
#
# Role tiers, reusing the sets already defined in app.core.permissions
# instead of inventing a parallel authorization system (same pattern as
# company_documents.py/agriculture_photos.py's verify-then-approve split):
#   PRODUCT_CONTRIBUTORS - owner + managers: create/submit product content
#   PRODUCT_MANAGERS     - same set as above: can send content back
#   CONTENT_VERIFIERS    - super_admin/admin/content_manager: the "verifier"
#   SETTINGS_MANAGERS    - super_admin/admin only: the "approver"/publisher
TRANSITION_RULES: dict[tuple[str, str], set[str]] = {
    ("draft", "pending_verification"): PRODUCT_CONTRIBUTORS,
    ("draft", "in_review"): PRODUCT_CONTRIBUTORS,
    ("draft", "archived"): PRODUCT_MANAGERS,
    ("pending_verification", "in_review"): CONTENT_VERIFIERS,
    ("pending_verification", "revision_required"): CONTENT_VERIFIERS,
    ("pending_verification", "draft"): PRODUCT_MANAGERS,
    ("in_review", "approved"): SETTINGS_MANAGERS,
    ("in_review", "rejected"): CONTENT_VERIFIERS,
    ("in_review", "revision_required"): CONTENT_VERIFIERS,
    ("in_review", "draft"): PRODUCT_MANAGERS,
    ("revision_required", "draft"): PRODUCT_MANAGERS,
    ("revision_required", "pending_verification"): PRODUCT_CONTRIBUTORS,
    ("approved", "published"): SETTINGS_MANAGERS,
    ("approved", "draft"): PRODUCT_MANAGERS,
    ("published", "unpublished"): SETTINGS_MANAGERS,
    ("published", "archived"): SETTINGS_MANAGERS,
    ("unpublished", "published"): SETTINGS_MANAGERS,
    ("unpublished", "archived"): SETTINGS_MANAGERS,
    ("archived", "draft"): PRODUCT_MANAGERS,
    ("rejected", "draft"): PRODUCT_MANAGERS,
}

VALID_TRANSITIONS: dict[str, set[str]] = {}
for (_from, _to), _roles in TRANSITION_RULES.items():
    VALID_TRANSITIONS.setdefault(_from, set()).add(_to)


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


def _pack_size_out(ps: ProductPackSize) -> dict:
    return {"id": ps.id, "quantity": ps.quantity, "unit": ps.unit, "packaging_type": ps.packaging_type,
            "sku": ps.sku, "price": float(ps.price) if ps.price is not None else None,
            "availability_status": ps.availability_status}


def _crop_out(c: ProductCrop) -> dict:
    return {"id": c.id, "crop_name": c.crop_name, "crop_category": c.crop_category,
            "target_use": c.target_use, "application_stage": c.application_stage}


def _claim_out(c: ProductClaim) -> dict:
    return {"id": c.id, "claim_text": c.claim_text, "category": c.category,
            "source_evidence": c.source_evidence, "verification_status": c.verification_status}


def _certification_out(c: ProductCertification) -> dict:
    return {"id": c.id, "name": c.name, "issuing_organization": c.issuing_organization,
            "certificate_number": c.certificate_number,
            "issue_date": c.issue_date.isoformat() if c.issue_date else None,
            "expiry_date": c.expiry_date.isoformat() if c.expiry_date else None,
            "media_id": c.media_id, "verification_status": c.verification_status}


def _document_out(d: ProductDocument) -> dict:
    return {"id": d.id, "document_type": d.document_type, "title": d.title, "version": d.version,
            "issue_date": d.issue_date.isoformat() if d.issue_date else None,
            "expiry_date": d.expiry_date.isoformat() if d.expiry_date else None,
            "document_number": d.document_number, "media_id": d.media_id,
            "verification_status": d.verification_status}


def _serialize(db: Session, p: Product, rating_summary: dict, *, public: bool = False) -> dict:
    pack_sizes = db.query(ProductPackSize).filter(ProductPackSize.product_id == p.id).order_by(ProductPackSize.sort_order).all()
    crops = db.query(ProductCrop).filter(ProductCrop.product_id == p.id).order_by(ProductCrop.sort_order).all()
    claims = db.query(ProductClaim).filter(ProductClaim.product_id == p.id).all()
    certifications = db.query(ProductCertification).filter(ProductCertification.product_id == p.id).all()
    documents = db.query(ProductDocument).filter(ProductDocument.product_id == p.id).all()
    if public:
        # A claim/certification/document is only shown publicly once
        # verified - an unverified one existing internally must never leak
        # onto the public product page, matching the "no unsupported claim"
        # rule from the spec.
        claims = [c for c in claims if c.verification_status == "verified"]
        certifications = [c for c in certifications if c.verification_status == "verified"]
        documents = [d for d in documents if d.verification_status == "verified"]

    return {
        "id": p.id, "sku": p.sku, "name": p.name, "slug": p.slug, "category_id": p.category_id,
        "product_type": p.product_type, "short_description": p.short_description,
        "full_description": p.full_description, "benefits": p.benefits,
        "recommended_crops": p.recommended_crops, "crop_stage": p.crop_stage,
        "application_method": p.application_method, "dosage_value": p.dosage_value,
        "dosage_unit": p.dosage_unit, "pack_sizes": p.pack_sizes,
        "manufacturing_date": p.manufacturing_date.isoformat() if p.manufacturing_date else None,
        "expiry_date": p.expiry_date.isoformat() if p.expiry_date else None,
        "precautions": p.precautions,
        "regulatory_notes": p.regulatory_notes,
        "active_ingredients": p.active_ingredients, "nutrient_content": p.nutrient_content,
        "concentration": p.concentration, "formulation": p.formulation, "grade": p.grade,
        "physical_form": p.physical_form, "technical_specifications": p.technical_specifications,
        "status": p.status, "featured": p.featured,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        "images": [{"id": i.id, "file_path": i.file_path, "alt_text": i.alt_text} for i in p.images],
        "pack_size_records": [_pack_size_out(x) for x in pack_sizes],
        "crops": [_crop_out(x) for x in crops],
        "claims": [_claim_out(x) for x in claims],
        "certifications": [_certification_out(x) for x in certifications],
        "documents": [_document_out(x) for x in documents],
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
    return {"total": total, "page": page, "page_size": page_size,
            "items": [_serialize(db, p, summaries[p.id], public=True) for p in items]}


@router.get("/public/{slug}")
def public_product_detail(slug: str, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.slug == slug, Product.status == "published").first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found.")
    out = _serialize(db, p, _rating_summaries(db, [p.id])[p.id], public=True)
    reviews = db.query(ProductReview).filter(ProductReview.product_id == p.id, ProductReview.status == "approved").order_by(ProductReview.created_at.desc()).all()
    out["reviews"] = [{"id": r.id, "reviewer_name": r.reviewer_name, "rating": r.rating, "comment": r.comment, "created_at": r.created_at.isoformat()} for r in reviews]
    return out


@router.get("")
def admin_list_products(status: str | None = None, page: int = 1, page_size: int = 20,
                         user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)),
                         db: Session = Depends(get_db)):
    query = db.query(Product).options(joinedload(Product.images))
    if status:
        query = query.filter(Product.status == status)
    total = query.count()
    items = query.order_by(Product.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    summaries = _rating_summaries(db, [p.id for p in items])
    return {"total": total, "items": [_serialize(db, p, summaries[p.id]) for p in items]}


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
    return _serialize(db, p, _rating_summaries(db, [p.id])[p.id])


@router.put("/{product_id}")
def update_product(product_id: str, payload: ProductUpdate, user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)),
                    db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found.")
    for field, value in payload.model_dump().items():
        setattr(p, field, value)
    p.updated_by_id = user.id
    record_audit(db, actor_id=user.id, action="product.update", entity_type="product", entity_id=p.id, summary=f"Updated product {p.name}")
    db.commit()
    db.refresh(p)
    return _serialize(db, p, _rating_summaries(db, [p.id])[p.id])


@router.post("/{product_id}/transition/{new_status}")
def transition_product(product_id: str, new_status: str, payload: ProductStatusChange,
                        user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)),
                        db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found.")
    rule_key = (p.status, new_status)
    if rule_key not in TRANSITION_RULES:
        raise HTTPException(status_code=400, detail=f"Cannot move product from '{p.status}' to '{new_status}'.")
    required_roles = TRANSITION_RULES[rule_key]
    if user.role not in required_roles:
        raise HTTPException(status_code=403, detail=f"You are not authorized to move a product from '{p.status}' to '{new_status}'.")

    if new_status == "published":
        missing = []
        if not p.category_id:
            missing.append("category")
        if not p.full_description:
            missing.append("full description")
        if not p.precautions:
            missing.append("precautions")
        if not p.images:
            missing.append("at least one product image")
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
    return _serialize(db, p, _rating_summaries(db, [p.id])[p.id])


@router.delete("/{product_id}")
def delete_product(product_id: str, user: User = Depends(require_roles("super_admin")), db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found.")
    record_audit(db, actor_id=user.id, action="product.delete", entity_type="product", entity_id=p.id, summary=f"Permanently deleted product {p.name}")
    # images/reviews cascade via their ORM relationship (cascade="all,
    # delete-orphan" on Product), but pack sizes/crops/claims/
    # certifications/documents are only ever queried ad hoc by product_id
    # elsewhere in this router - no relationship means no cascade, so
    # deleting a product with any of these left it 500ing on a foreign key
    # violation instead of actually deleting anything.
    for model in (ProductPackSize, ProductCrop, ProductClaim, ProductCertification, ProductDocument):
        db.query(model).filter(model.product_id == p.id).delete()
    db.delete(p)
    db.commit()
    return {"ok": True}


def _get_product_or_404(db: Session, product_id: str) -> Product:
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found.")
    return p


# --- Images ----------------------------------------------------------------
# Upload itself lives in media.py (POST /media/products/{id}/images) since it
# handles the file; removal is a plain sub-resource delete like every other
# product child record below.

@router.delete("/{product_id}/images/{image_id}")
def remove_image(product_id: str, image_id: str, user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)), db: Session = Depends(get_db)):
    p = _get_product_or_404(db, product_id)
    row = db.get(ProductImage, image_id)
    if not row or row.product_id != p.id:
        raise HTTPException(status_code=404, detail="Image not found.")
    db.delete(row)
    record_audit(db, actor_id=user.id, action="product.image.remove", entity_type="product", entity_id=p.id,
                 summary=f"Image removed from {p.name}")
    db.commit()
    return {"ok": True}


# --- Pack sizes ---------------------------------------------------------

@router.post("/{product_id}/pack-sizes")
def add_pack_size(product_id: str, payload: ProductPackSizeCreate,
                   user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)), db: Session = Depends(get_db)):
    p = _get_product_or_404(db, product_id)
    row = ProductPackSize(product_id=p.id, sort_order=db.query(ProductPackSize).filter(ProductPackSize.product_id == p.id).count(),
                           **payload.model_dump())
    db.add(row)
    record_audit(db, actor_id=user.id, action="product.pack_size.add", entity_type="product", entity_id=p.id,
                 summary=f"Pack size added to {p.name}: {payload.quantity} {payload.unit}")
    db.commit()
    return _pack_size_out(row)


@router.delete("/{product_id}/pack-sizes/{pack_size_id}")
def remove_pack_size(product_id: str, pack_size_id: str,
                      user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)), db: Session = Depends(get_db)):
    p = _get_product_or_404(db, product_id)
    row = db.get(ProductPackSize, pack_size_id)
    if not row or row.product_id != p.id:
        raise HTTPException(status_code=404, detail="Pack size not found.")
    db.delete(row)
    record_audit(db, actor_id=user.id, action="product.pack_size.remove", entity_type="product", entity_id=p.id, summary=f"Pack size removed from {p.name}")
    db.commit()
    return {"ok": True}


# --- Crops ---------------------------------------------------------------

@router.post("/{product_id}/crops")
def add_crop(product_id: str, payload: ProductCropCreate,
             user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)), db: Session = Depends(get_db)):
    p = _get_product_or_404(db, product_id)
    row = ProductCrop(product_id=p.id, sort_order=db.query(ProductCrop).filter(ProductCrop.product_id == p.id).count(),
                       **payload.model_dump())
    db.add(row)
    record_audit(db, actor_id=user.id, action="product.crop.add", entity_type="product", entity_id=p.id,
                 summary=f"Crop association added to {p.name}: {payload.crop_name}")
    db.commit()
    return _crop_out(row)


@router.delete("/{product_id}/crops/{crop_id}")
def remove_crop(product_id: str, crop_id: str,
                 user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)), db: Session = Depends(get_db)):
    p = _get_product_or_404(db, product_id)
    row = db.get(ProductCrop, crop_id)
    if not row or row.product_id != p.id:
        raise HTTPException(status_code=404, detail="Crop association not found.")
    db.delete(row)
    record_audit(db, actor_id=user.id, action="product.crop.remove", entity_type="product", entity_id=p.id, summary=f"Crop association removed from {p.name}")
    db.commit()
    return {"ok": True}


# --- Claims ----------------------------------------------------------------

@router.post("/{product_id}/claims")
def add_claim(product_id: str, payload: ProductClaimCreate,
              user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)), db: Session = Depends(get_db)):
    p = _get_product_or_404(db, product_id)
    row = ProductClaim(product_id=p.id, **payload.model_dump())
    db.add(row)
    record_audit(db, actor_id=user.id, action="product.claim.add", entity_type="product", entity_id=p.id, summary=f"Claim added to {p.name}")
    db.commit()
    return _claim_out(row)


@router.post("/{product_id}/claims/{claim_id}/verify")
def verify_claim(product_id: str, claim_id: str, payload: VerificationStatusChange,
                  user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    """A claim is never shown on the public product page until a verifier
    (never the submitter) marks it verified - see _serialize's public
    filtering above."""
    p = _get_product_or_404(db, product_id)
    row = db.get(ProductClaim, claim_id)
    if not row or row.product_id != p.id:
        raise HTTPException(status_code=404, detail="Claim not found.")
    row.verification_status = payload.verification_status
    row.verified_by_id = user.id
    row.verified_at = dt.datetime.utcnow()
    record_audit(db, actor_id=user.id, action="product.claim.verify", entity_type="product", entity_id=p.id,
                 summary=f"Claim on {p.name} marked {payload.verification_status}")
    db.commit()
    return _claim_out(row)


@router.delete("/{product_id}/claims/{claim_id}")
def remove_claim(product_id: str, claim_id: str,
                  user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)), db: Session = Depends(get_db)):
    p = _get_product_or_404(db, product_id)
    row = db.get(ProductClaim, claim_id)
    if not row or row.product_id != p.id:
        raise HTTPException(status_code=404, detail="Claim not found.")
    db.delete(row)
    record_audit(db, actor_id=user.id, action="product.claim.remove", entity_type="product", entity_id=p.id, summary=f"Claim removed from {p.name}")
    db.commit()
    return {"ok": True}


# --- Certifications ----------------------------------------------------

@router.post("/{product_id}/certifications")
def add_certification(product_id: str, payload: ProductCertificationCreate,
                       user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)), db: Session = Depends(get_db)):
    p = _get_product_or_404(db, product_id)
    row = ProductCertification(product_id=p.id, **payload.model_dump())
    db.add(row)
    record_audit(db, actor_id=user.id, action="product.certification.add", entity_type="product", entity_id=p.id,
                 summary=f"Certification added to {p.name}: {payload.name}")
    db.commit()
    return _certification_out(row)


@router.post("/{product_id}/certifications/{certification_id}/verify")
def verify_certification(product_id: str, certification_id: str, payload: VerificationStatusChange,
                          user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    p = _get_product_or_404(db, product_id)
    row = db.get(ProductCertification, certification_id)
    if not row or row.product_id != p.id:
        raise HTTPException(status_code=404, detail="Certification not found.")
    row.verification_status = payload.verification_status
    record_audit(db, actor_id=user.id, action="product.certification.verify", entity_type="product", entity_id=p.id,
                 summary=f"Certification on {p.name} marked {payload.verification_status}")
    db.commit()
    return _certification_out(row)


@router.delete("/{product_id}/certifications/{certification_id}")
def remove_certification(product_id: str, certification_id: str,
                          user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)), db: Session = Depends(get_db)):
    p = _get_product_or_404(db, product_id)
    row = db.get(ProductCertification, certification_id)
    if not row or row.product_id != p.id:
        raise HTTPException(status_code=404, detail="Certification not found.")
    db.delete(row)
    record_audit(db, actor_id=user.id, action="product.certification.remove", entity_type="product", entity_id=p.id, summary=f"Certification removed from {p.name}")
    db.commit()
    return {"ok": True}


# --- Documents (technical data sheets, SDS, labels, brochures, ...) ------

@router.post("/{product_id}/documents")
def add_document(product_id: str, payload: ProductDocumentCreate,
                  user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)), db: Session = Depends(get_db)):
    """Metadata only - the actual file is uploaded first via
    POST /api/v1/media/products/{product_id}/documents, which returns the
    media_id this call references."""
    p = _get_product_or_404(db, product_id)
    row = ProductDocument(product_id=p.id, uploaded_by_id=user.id, **payload.model_dump())
    db.add(row)
    record_audit(db, actor_id=user.id, action="product.document.add", entity_type="product", entity_id=p.id,
                 summary=f"Document added to {p.name}: {payload.title} ({payload.document_type})")
    db.commit()
    return _document_out(row)


@router.post("/{product_id}/documents/{document_id}/verify")
def verify_document(product_id: str, document_id: str, payload: VerificationStatusChange,
                     user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    """Covers the official label/package artwork too (document_type="label")
    - it must be verified here, same as any other product document, before
    _serialize's public filtering will ever include it."""
    p = _get_product_or_404(db, product_id)
    row = db.get(ProductDocument, document_id)
    if not row or row.product_id != p.id:
        raise HTTPException(status_code=404, detail="Document not found.")
    row.verification_status = payload.verification_status
    row.reviewed_by_id = user.id
    row.reviewed_at = dt.datetime.utcnow()
    record_audit(db, actor_id=user.id, action="product.document.verify", entity_type="product", entity_id=p.id,
                 summary=f"Document on {p.name} marked {payload.verification_status}")
    db.commit()
    return _document_out(row)


@router.delete("/{product_id}/documents/{document_id}")
def remove_document(product_id: str, document_id: str,
                     user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)), db: Session = Depends(get_db)):
    p = _get_product_or_404(db, product_id)
    row = db.get(ProductDocument, document_id)
    if not row or row.product_id != p.id:
        raise HTTPException(status_code=404, detail="Document not found.")
    db.delete(row)
    record_audit(db, actor_id=user.id, action="product.document.remove", entity_type="product", entity_id=p.id, summary=f"Document removed from {p.name}")
    db.commit()
    return {"ok": True}
