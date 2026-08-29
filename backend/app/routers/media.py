"""
File upload and retrieval.

- Product images: public, uploaded by product managers, attached to a
  product's `images` list.
- Case attachments: private, uploaded by the case's farmer or by staff/
  dealer with access to that case; served only to viewers with case access.
- Dealer documents: private, uploaded during/after a dealer application;
  served only to dealer managers and the owning dealer.
"""
import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core import storage
from app.core.audit import record_audit
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles, require_user
from app.core.permissions import CASE_MANAGERS, CONTENT_VERIFIERS, DEALER_MANAGERS, PRODUCT_CONTRIBUTORS, PRODUCT_MANAGERS, ROLE_DEALER, ROLE_FARMER
from app.core.uploads import validate_and_store
from app.models.models import AgriculturePhoto, CompanyDocument, DealerProfile, FarmerSupportCase, MediaRecord, Product, ProductImage, User

router = APIRouter(prefix="/api/v1/media", tags=["media"])
settings = get_settings()


@router.post("/products/{product_id}/images")
def upload_product_image(product_id: str, file: UploadFile, alt_text: str = "",
                          user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)),
                          db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    if not alt_text.strip():
        raise HTTPException(status_code=400, detail="Alt text is required for product images.")

    path, original_name, content_type, size = validate_and_store(
        file, is_public=True, allow_pdf=False, max_size_bytes=settings.MAX_IMAGE_SIZE_BYTES,
    )
    record = MediaRecord(file_path=path, original_filename=original_name, content_type=content_type, size_bytes=size,
                          is_public=True, purpose="product_image", entity_type="product", entity_id=product_id,
                          alt_text=alt_text, uploaded_by_id=user.id)
    db.add(record)
    db.flush()
    order = len(product.images)
    image = ProductImage(product_id=product_id, file_path=path, alt_text=alt_text, sort_order=order)
    db.add(image)
    record_audit(db, actor_id=user.id, action="media.upload_product_image", entity_type="product", entity_id=product_id,
                 summary=f"Image uploaded for product {product.name}")
    db.commit()
    return {"id": image.id, "file_path": path, "alt_text": alt_text}


@router.post("/products/{product_id}/labels")
def upload_product_label(product_id: str, file: UploadFile,
                          user: User = Depends(require_roles(*PRODUCT_MANAGERS, "super_admin")),
                          db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    path, original_name, content_type, size = validate_and_store(
        file, is_public=True, allow_pdf=True, max_size_bytes=settings.MAX_DOCUMENT_SIZE_BYTES,
    )
    record = MediaRecord(file_path=path, original_filename=original_name, content_type=content_type, size_bytes=size,
                          is_public=True, purpose="product_label", entity_type="product", entity_id=product_id,
                          uploaded_by_id=user.id)
    db.add(record)
    record_audit(db, actor_id=user.id, action="media.upload_product_label", entity_type="product", entity_id=product_id,
                 summary=f"Label document uploaded for product {product.name}")
    db.commit()
    return {"file_path": path, "original_filename": original_name}


@router.post("/products/{product_id}/documents")
def upload_product_document_file(product_id: str, file: UploadFile,
                                  user: User = Depends(require_roles(*PRODUCT_CONTRIBUTORS)),
                                  db: Session = Depends(get_db)):
    """Uploads the underlying file only - same two-step pattern as company
    documents. The caller then creates a ProductDocument record (POST
    /api/v1/products/{product_id}/documents) referencing the returned id,
    covering technical data sheets, safety data sheets, certificates,
    registration documents, the official label artwork, brochures, and
    other approved product documents - none of which are shown publicly
    until a verifier marks them verified (see products.py verify_document)."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    path, original_name, content_type, size = validate_and_store(
        file, is_public=True, allow_pdf=True, max_size_bytes=settings.MAX_DOCUMENT_SIZE_BYTES,
    )
    record = MediaRecord(file_path=path, original_filename=original_name, content_type=content_type, size_bytes=size,
                          is_public=True, purpose="product_document", entity_type="product", entity_id=product_id,
                          uploaded_by_id=user.id)
    db.add(record)
    db.flush()
    record_audit(db, actor_id=user.id, action="media.upload_product_document", entity_type="product", entity_id=product_id,
                 summary=f"Document file uploaded for product {product.name}")
    db.commit()
    return {"id": record.id, "original_filename": original_name}


def _assert_case_access(db: Session, case_id: str, user: User) -> FarmerSupportCase:
    case = db.get(FarmerSupportCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    if user.role in CASE_MANAGERS:
        return case
    if user.role == ROLE_FARMER:
        if case.farmer_id != user.id:
            raise HTTPException(status_code=403, detail="You do not have access to this case.")
        return case
    if user.role == ROLE_DEALER:
        profile = db.query(DealerProfile).filter(DealerProfile.user_id == user.id).first()
        if not profile or case.assigned_dealer_id != profile.id:
            raise HTTPException(status_code=403, detail="You do not have access to this case.")
        return case
    # Any other role (content_manager, distributor, etc.) has no business
    # relationship to farmer support cases at all - deny by default rather
    # than falling through unrestricted.
    raise HTTPException(status_code=403, detail="You do not have access to this case.")


@router.post("/cases/{case_id}/attachments")
def upload_case_attachment(case_id: str, file: UploadFile, user: User = Depends(require_user), db: Session = Depends(get_db)):
    case = _assert_case_access(db, case_id, user)
    path, original_name, content_type, size = validate_and_store(
        file, is_public=False, allow_pdf=True, max_size_bytes=settings.MAX_DOCUMENT_SIZE_BYTES,
    )
    record = MediaRecord(file_path=path, original_filename=original_name, content_type=content_type, size_bytes=size,
                          is_public=False, purpose="case_attachment", entity_type="farmer_support_case", entity_id=case.id,
                          uploaded_by_id=user.id)
    db.add(record)
    db.flush()
    from app.models.models import CaseMessage
    db.add(CaseMessage(case_id=case.id, author_id=user.id, body=f"Attachment uploaded: {original_name}", event_type="attachment"))
    record_audit(db, actor_id=user.id, action="media.upload_case_attachment", entity_type="farmer_support_case", entity_id=case.id,
                 summary=f"Attachment uploaded to case {case.reference_number}")
    db.commit()
    return {"id": record.id, "original_filename": original_name}


@router.get("/cases/{case_id}/attachments")
def list_case_attachments(case_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    _assert_case_access(db, case_id, user)
    records = db.query(MediaRecord).filter(MediaRecord.entity_type == "farmer_support_case", MediaRecord.entity_id == case_id).all()
    return [{"id": r.id, "original_filename": r.original_filename, "created_at": r.created_at.isoformat()} for r in records]


@router.post("/dealer-applications/{application_id}/documents")
def upload_dealer_document(application_id: str, file: UploadFile, user: User | None = Depends(get_current_user), db: Session = Depends(get_db)):
    # Public endpoint: a dealer applicant is usually not signed in yet.
    # Access is scoped by knowing the application's unguessable ID, which
    # is only returned to the applicant at submission time.
    from app.models.models import DealerApplication
    application = db.get(DealerApplication, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")
    path, original_name, content_type, size = validate_and_store(
        file, is_public=False, allow_pdf=True, max_size_bytes=settings.MAX_DOCUMENT_SIZE_BYTES,
    )
    record = MediaRecord(file_path=path, original_filename=original_name, content_type=content_type, size_bytes=size,
                          is_public=False, purpose="dealer_document", entity_type="dealer_application", entity_id=application.id,
                          uploaded_by_id=user.id if user else None)
    db.add(record)
    record_audit(db, actor_id=user.id if user else None, action="media.upload_dealer_document", entity_type="dealer_application",
                 entity_id=application.id, summary=f"Document uploaded for application {application.reference_number}")
    db.commit()
    return {"id": record.id, "original_filename": original_name}


@router.get("/dealer-applications/{application_id}/documents")
def list_dealer_documents(application_id: str, user: User = Depends(require_roles(*DEALER_MANAGERS)), db: Session = Depends(get_db)):
    records = db.query(MediaRecord).filter(MediaRecord.entity_type == "dealer_application", MediaRecord.entity_id == application_id).all()
    return [{"id": r.id, "original_filename": r.original_filename, "created_at": r.created_at.isoformat()} for r in records]


CORPORATE_MEDIA_PURPOSES = {
    "leadership_photo", "manufacturing_photo", "manufacturing_document",
    "research_photo", "research_document", "certification_document",
    "sustainability_photo", "sustainability_document",
}


@router.post("/corporate/{purpose}")
def upload_corporate_media(purpose: str, file: UploadFile, alt_text: str = "",
                            user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    """Backs photo/document uploads for the Leadership, Manufacturing,
    Research & Development, Quality & Safety, and Sustainability CMS
    sections - owner/manager (CONTENT_VERIFIERS) only, matching every other
    corporate-content create endpoint. Uploading a file never verifies or
    publishes anything by itself; the caller then references the returned
    id from the matching domain record (e.g. LeadershipProfile.photo_media_id)."""
    if purpose not in CORPORATE_MEDIA_PURPOSES:
        raise HTTPException(status_code=400, detail="Invalid upload purpose.")
    allow_pdf = purpose.endswith("_document")
    max_size = settings.MAX_DOCUMENT_SIZE_BYTES if allow_pdf else settings.MAX_IMAGE_SIZE_BYTES
    path, original_name, content_type, size = validate_and_store(file, is_public=True, allow_pdf=allow_pdf, max_size_bytes=max_size)
    record = MediaRecord(file_path=path, original_filename=original_name, content_type=content_type, size_bytes=size,
                          is_public=True, purpose=purpose, alt_text=alt_text or None, uploaded_by_id=user.id)
    db.add(record)
    db.flush()
    record_audit(db, actor_id=user.id, action="media.upload_corporate", entity_type="media_record", entity_id=record.id,
                 summary=f"Corporate media uploaded ({purpose}): {original_name}")
    db.commit()
    return {"id": record.id, "file_path": path, "original_filename": original_name}


@router.post("/company-documents")
def upload_company_document_file(file: UploadFile, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    """Uploads the underlying file only. The caller then creates a
    CompanyDocument record (POST /api/company/documents) referencing this
    media id - uploading a file never verifies or publishes it by itself."""
    path, original_name, content_type, size = validate_and_store(
        file, is_public=False, allow_pdf=True, max_size_bytes=settings.MAX_DOCUMENT_SIZE_BYTES,
    )
    record = MediaRecord(file_path=path, original_filename=original_name, content_type=content_type, size_bytes=size,
                          is_public=False, purpose="company_document", uploaded_by_id=user.id)
    db.add(record)
    record_audit(db, actor_id=user.id, action="media.upload_company_document", entity_type="media_record", entity_id=record.id,
                 summary=f"Company document file uploaded: {original_name}")
    db.commit()
    db.refresh(record)
    return {"id": record.id, "original_filename": original_name}


@router.post("/agriculture-photos")
def upload_agriculture_photo_file(file: UploadFile, user: User = Depends(require_roles(*CONTENT_VERIFIERS)), db: Session = Depends(get_db)):
    """Uploads the underlying image only, stored privately - it is only
    ever served through GET /api/media/gallery/{agriculture_photo_id},
    which checks the photo's own status is "published" first."""
    path, original_name, content_type, size = validate_and_store(
        file, is_public=False, allow_pdf=False, max_size_bytes=settings.MAX_IMAGE_SIZE_BYTES,
    )
    record = MediaRecord(file_path=path, original_filename=original_name, content_type=content_type, size_bytes=size,
                          is_public=False, purpose="agriculture_photo", uploaded_by_id=user.id)
    db.add(record)
    record_audit(db, actor_id=user.id, action="media.upload_agriculture_photo", entity_type="media_record", entity_id=record.id,
                 summary=f"Agriculture photo file uploaded: {original_name}")
    db.commit()
    db.refresh(record)
    return {"id": record.id, "original_filename": original_name}


@router.get("/gallery/{photo_id}")
def serve_agriculture_photo(photo_id: str, db: Session = Depends(get_db)):
    """Public image endpoint for an agriculture photo - only serves
    photos whose status is "published", regardless of who requests it."""
    photo = db.get(AgriculturePhoto, photo_id)
    if not photo or photo.status != "published":
        raise HTTPException(status_code=404, detail="Photo not found.")
    record = db.get(MediaRecord, photo.media_id)
    if not record:
        raise HTTPException(status_code=404, detail="Photo not found.")
    content = storage.load(record.file_path)
    if content is None:
        raise HTTPException(status_code=404, detail="Photo not found.")
    return Response(content=content, media_type=record.content_type)


@router.get("/certificates/{document_id}")
def serve_company_document(document_id: str, db: Session = Depends(get_db)):
    """Public download endpoint for a company certificate/document - only
    serves documents that are both verified and explicitly published."""
    doc = db.get(CompanyDocument, document_id)
    if not doc or not doc.is_published or doc.verification_status != "verified":
        raise HTTPException(status_code=404, detail="Document not found.")
    record = db.get(MediaRecord, doc.media_id)
    if not record:
        raise HTTPException(status_code=404, detail="Document not found.")
    content = storage.load(record.file_path)
    if content is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return Response(
        content=content, media_type=record.content_type,
        headers={"Content-Disposition": f'attachment; filename="{record.original_filename}"'},
    )


@router.get("/public/{subpath:path}")
def serve_public_file(subpath: str, db: Session = Depends(get_db)):
    # subpath comes straight from the URL - reject traversal attempts
    # (a "..") or an absolute-looking path before ever building a storage
    # key, regardless of which storage backend is active.
    if not subpath or subpath.startswith("/") or ".." in Path(subpath).parts:
        raise HTTPException(status_code=404, detail="File not found.")
    relative_path = f"{settings.PUBLIC_UPLOAD_SUBDIR}/{subpath}"
    content = storage.load(relative_path)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found.")
    record = db.query(MediaRecord).filter(MediaRecord.file_path == relative_path).first()
    content_type = record.content_type if record else (mimetypes.guess_type(subpath)[0] or "application/octet-stream")
    return Response(content=content, media_type=content_type)


@router.get("/private/{record_id}")
def serve_private_file(record_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    record = db.get(MediaRecord, record_id)
    if not record or record.is_public:
        raise HTTPException(status_code=404, detail="File not found.")

    if record.purpose == "case_attachment":
        _assert_case_access(db, record.entity_id, user)
    elif record.purpose == "dealer_document":
        is_owning_dealer = (
            user.role == ROLE_DEALER
            and db.query(DealerProfile)
            .filter(DealerProfile.user_id == user.id, DealerProfile.application_id == record.entity_id)
            .first()
            is not None
        )
        if user.role not in DEALER_MANAGERS and not is_owning_dealer:
            raise HTTPException(status_code=403, detail="You do not have access to this file.")
    else:
        raise HTTPException(status_code=403, detail="You do not have access to this file.")

    content = storage.load(record.file_path)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found.")
    return Response(
        content=content, media_type=record.content_type,
        headers={"Content-Disposition": f'attachment; filename="{record.original_filename}"'},
    )
