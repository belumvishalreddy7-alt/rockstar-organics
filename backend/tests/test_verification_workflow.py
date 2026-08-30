"""Tests for the extended certificate/agriculture-photo verification
workflow added 2026-08-28: the approve/publish/archive gate restricted to
Super Administrator/Administrator, and the submitted/rejected/version
metadata now tracked on both entity types."""
import uuid


def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200


def _invite_content_manager(client, super_admin):
    _, admin_email, admin_password = super_admin
    _login(client, admin_email, admin_password)
    suffix = uuid.uuid4().hex[:8]
    email = f"contentmgr-{suffix}@example.com"
    r = client.post("/api/v1/staff/invite", json={"email": email, "full_name": "Content Mgr", "role": "content_manager"})
    assert r.status_code == 200, r.text
    password = r.json()["temporary_password"]
    client.post("/api/v1/auth/logout")
    return email, password


def _upload_and_verify_document(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)
    upload = client.post("/api/v1/media/company-documents", files={"file": ("c.pdf", b"%PDF-1.4 x", "application/pdf")})
    media_id = upload.json()["id"]
    create = client.post("/api/v1/company/documents", json={
        "title": "RBAC Test Certificate", "document_type": "quality_certificate", "media_id": media_id,
    })
    doc_id = create.json()["id"]
    verify = client.post(f"/api/v1/company/documents/{doc_id}/verify/verified", json={"notes": "ok"})
    assert verify.status_code == 200
    client.post("/api/v1/auth/logout")
    return doc_id


def test_content_manager_can_verify_but_not_approve_certificate(client, super_admin):
    doc_id = _upload_and_verify_document(client, super_admin)
    cm_email, cm_password = _invite_content_manager(client, super_admin)
    _login(client, cm_email, cm_password)

    approve = client.post(f"/api/v1/company/documents/{doc_id}/approve")
    assert approve.status_code == 403

    publish = client.post(f"/api/v1/company/documents/{doc_id}/publish")
    assert publish.status_code == 403

    archive = client.post(f"/api/v1/company/documents/{doc_id}/archive")
    assert archive.status_code == 403
    client.post("/api/v1/auth/logout")


def test_administrator_can_approve_publish_and_archive_certificate(client, super_admin):
    _, admin_email, admin_password = super_admin
    doc_id = _upload_and_verify_document(client, super_admin)
    _login(client, admin_email, admin_password)

    approve = client.post(f"/api/v1/company/documents/{doc_id}/approve")
    assert approve.status_code == 200
    assert approve.json()["is_approved"] is True
    assert approve.json()["approved_by_id"]

    publish = client.post(f"/api/v1/company/documents/{doc_id}/publish")
    assert publish.status_code == 200
    assert publish.json()["published_at"]

    archive = client.post(f"/api/v1/company/documents/{doc_id}/archive")
    assert archive.status_code == 200
    assert archive.json()["is_published"] is False  # archiving always pulls it off the public site

    unarchive = client.post(f"/api/v1/company/documents/{doc_id}/unarchive")
    assert unarchive.status_code == 200
    assert unarchive.json()["is_archived"] is False
    client.post("/api/v1/auth/logout")


def test_re_verification_resets_approval(client, super_admin):
    """If a verified+approved document is sent back through verification
    (e.g. an expiry was found), its approval must not silently survive -
    otherwise it could be republished without a fresh administrator sign-off."""
    _, admin_email, admin_password = super_admin
    doc_id = _upload_and_verify_document(client, super_admin)
    _login(client, admin_email, admin_password)
    client.post(f"/api/v1/company/documents/{doc_id}/approve")

    reverify = client.post(f"/api/v1/company/documents/{doc_id}/verify/under_review", json={})
    assert reverify.status_code == 200
    assert reverify.json()["is_approved"] is False

    publish_blocked = client.post(f"/api/v1/company/documents/{doc_id}/publish")
    assert publish_blocked.status_code == 400
    client.post("/api/v1/auth/logout")


def test_rejected_certificate_records_reason(client, super_admin):
    _, admin_email, admin_password = super_admin
    _login(client, admin_email, admin_password)
    upload = client.post("/api/v1/media/company-documents", files={"file": ("c.pdf", b"%PDF-1.4 x", "application/pdf")})
    media_id = upload.json()["id"]
    create = client.post("/api/v1/company/documents", json={
        "title": "Reject Me", "document_type": "other", "media_id": media_id,
    })
    doc_id = create.json()["id"]
    r = client.post(f"/api/v1/company/documents/{doc_id}/verify/rejected", json={"rejection_reason": "Reference number does not match the issuing body's register."})
    assert r.status_code == 200
    assert "does not match" in r.json()["rejection_reason"]
    client.post("/api/v1/auth/logout")


def test_agriculture_photo_rejection_and_resubmission(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)
    upload = client.post("/api/v1/media/agriculture-photos", files={"file": ("f.jpg", b"\xff\xd8\xff\xe0x", "image/jpeg")})
    media_id = upload.json()["id"]
    create = client.post("/api/v1/media/agriculture", json={
        "title": "Field", "category": "fields", "alt_text": "A field.", "media_id": media_id, "usage_rights_verified": True,
    })
    photo_id = create.json()["id"]

    rejected = client.post(f"/api/v1/media/agriculture/{photo_id}/status/rejected", json={"rejection_reason": "Not our field - stock photo."})
    assert rejected.status_code == 200
    assert rejected.json()["rejection_reason"] == "Not our field - stock photo."

    # Staff can send it back to draft and resubmit through the workflow again.
    back_to_draft = client.post(f"/api/v1/media/agriculture/{photo_id}/status/draft", json={})
    assert back_to_draft.status_code == 200
    approve = client.post(f"/api/v1/media/agriculture/{photo_id}/status/approved", json={})
    assert approve.status_code == 200
    assert approve.json()["approved_by_id"]
    client.post("/api/v1/auth/logout")


def test_agriculture_photo_admin_preview_and_removal(client, super_admin, sales_manager):
    _, email, password = super_admin
    _login(client, email, password)
    upload = client.post("/api/v1/media/agriculture-photos", files={"file": ("f.jpg", b"\xff\xd8\xff\xe0x", "image/jpeg")})
    media_id = upload.json()["id"]
    create = client.post("/api/v1/media/agriculture", json={
        "title": "Draft Field", "category": "fields", "alt_text": "A field.", "media_id": media_id,
    })
    photo_id = create.json()["id"]
    assert create.json()["status"] == "draft"

    # The photo isn't published yet - the public endpoint must 404, but the
    # admin preview (what the review queue's thumbnail actually calls) works.
    assert client.get(f"/api/v1/media/gallery/{photo_id}").status_code == 404
    admin_preview = client.get(f"/api/v1/media/gallery/{photo_id}/admin")
    assert admin_preview.status_code == 200
    assert admin_preview.content == b"\xff\xd8\xff\xe0x"
    client.post("/api/v1/auth/logout")

    # A staff role outside CONTENT_VERIFIERS can't use the admin preview or delete.
    _, sm_email, sm_password = sales_manager
    _login(client, sm_email, sm_password)
    assert client.get(f"/api/v1/media/gallery/{photo_id}/admin").status_code == 403
    assert client.delete(f"/api/v1/media/agriculture/{photo_id}").status_code == 403
    client.post("/api/v1/auth/logout")

    _login(client, email, password)
    deleted = client.delete(f"/api/v1/media/agriculture/{photo_id}")
    assert deleted.status_code == 200
    assert client.get(f"/api/v1/media/gallery/{photo_id}/admin").status_code == 404
    assert client.delete("/api/v1/media/agriculture/nonexistent-id").status_code == 404
    client.post("/api/v1/auth/logout")
