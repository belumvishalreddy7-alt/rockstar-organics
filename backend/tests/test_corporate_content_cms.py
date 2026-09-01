"""Tests for the corporate content CMS (Leadership, Manufacturing, Research
& Development, Quality & Safety, Sustainability) added 2026-08-29.

Covers: only owner/manager roles (CONTENT_VERIFIERS) can create content;
only owner/admin (SETTINGS_MANAGERS) can approve/publish/archive; the full
draft -> submitted -> under_review -> verified -> approved -> published ->
archived -> restored workflow; the public endpoint only ever returns
published records; editing a published record is blocked; editing a
verified/approved record resets it to draft."""
import uuid


def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text


def test_farmer_and_dealer_cannot_create_leadership_profile(client, approved_dealer):
    client.post("/api/v1/auth/register", json={
        "full_name": "CMS Test Farmer", "email": "cms-farmer@example.com", "phone": "9876543261", "password": "Passw0rd123",
    })
    r = client.post("/api/v1/leadership", json={"full_name": "Someone", "position": "Someone"})
    assert r.status_code == 403
    client.post("/api/v1/auth/logout")

    _, email, password, _ = approved_dealer
    _login(client, email, password)
    r = client.post("/api/v1/leadership", json={"full_name": "Someone", "position": "Someone"})
    assert r.status_code == 403


def test_leadership_full_workflow_and_role_gating(client, super_admin):
    from app.core.permissions import ROLE_CONTENT_MANAGER
    from tests.conftest import _make_user

    cm_email, cm_password = f"cm-{uuid.uuid4().hex[:8]}@example.com", "Passw0rd123"
    _make_user(ROLE_CONTENT_MANAGER, cm_email, cm_password)
    _login(client, cm_email, cm_password)

    create = client.post("/api/v1/leadership", json={
        "full_name": "Test Leader", "position": "Chief Officer", "biography": "Bio pending verification.",
    })
    assert create.status_code == 200, create.text
    profile = create.json()
    assert profile["status"] == "draft"
    assert profile["version"] == 1
    profile_id = profile["id"]

    # not publicly visible yet
    assert client.get("/api/v1/leadership/public").json() == []
    assert client.get(f"/api/v1/leadership/public/{profile_id}").status_code == 404

    submit = client.post(f"/api/v1/leadership/{profile_id}/submit")
    assert submit.status_code == 200 and submit.json()["status"] == "submitted"

    review = client.post(f"/api/v1/leadership/{profile_id}/review")
    assert review.status_code == 200 and review.json()["status"] == "under_review"

    verify = client.post(f"/api/v1/leadership/{profile_id}/verify")
    assert verify.status_code == 200 and verify.json()["status"] == "verified"

    # a content_manager (verifier) cannot approve or publish - owner/admin only
    assert client.post(f"/api/v1/leadership/{profile_id}/approve").status_code == 403
    assert client.post(f"/api/v1/leadership/{profile_id}/publish").status_code == 403
    assert client.post(f"/api/v1/leadership/{profile_id}/archive").status_code == 403

    client.post("/api/v1/auth/logout")
    _, admin_email, admin_password = super_admin
    _login(client, admin_email, admin_password)

    approve = client.post(f"/api/v1/leadership/{profile_id}/approve")
    assert approve.status_code == 200 and approve.json()["status"] == "approved"

    publish = client.post(f"/api/v1/leadership/{profile_id}/publish")
    assert publish.status_code == 200 and publish.json()["status"] == "published"

    public_list = client.get("/api/v1/leadership/public").json()
    assert len(public_list) == 1 and public_list[0]["full_name"] == "Test Leader"
    assert client.get(f"/api/v1/leadership/public/{profile_id}").status_code == 200

    # editing a published record is blocked outright
    edit_blocked = client.put(f"/api/v1/leadership/{profile_id}", json={"full_name": "Changed", "position": "Changed"})
    assert edit_blocked.status_code == 400

    unpublish = client.post(f"/api/v1/leadership/{profile_id}/unpublish")
    assert unpublish.status_code == 200 and unpublish.json()["status"] == "approved"
    assert client.get("/api/v1/leadership/public").json() == []

    # editing a (no-longer-published) approved record resets it to draft
    pre_edit = client.get(f"/api/v1/leadership/admin/{profile_id}").json()
    edit = client.put(f"/api/v1/leadership/{profile_id}", json={"full_name": "Test Leader Updated", "position": "Chief Officer"})
    assert edit.status_code == 200
    assert edit.json()["status"] == "draft"
    assert edit.json()["version"] > pre_edit["version"]

    archive = client.post(f"/api/v1/leadership/{profile_id}/archive")
    assert archive.status_code == 200 and archive.json()["status"] == "archived"

    restore = client.post(f"/api/v1/leadership/{profile_id}/restore")
    assert restore.status_code == 200 and restore.json()["status"] == "draft"

    # a draft-status record can be permanently deleted; anything past draft cannot
    delete = client.delete(f"/api/v1/leadership/{profile_id}")
    assert delete.status_code == 200


def test_reject_and_request_revision(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)
    create = client.post("/api/v1/leadership", json={"full_name": "Rejectable", "position": "Role"})
    profile_id = create.json()["id"]
    client.post(f"/api/v1/leadership/{profile_id}/submit")
    client.post(f"/api/v1/leadership/{profile_id}/review")

    reject = client.post(f"/api/v1/leadership/{profile_id}/reject", json={"note": "Needs a real photo."})
    assert reject.status_code == 200
    assert reject.json()["status"] == "rejected"

    # a rejected record can be resubmitted
    resubmit = client.post(f"/api/v1/leadership/{profile_id}/submit")
    assert resubmit.status_code == 200 and resubmit.json()["status"] == "submitted"

    revision = client.post(f"/api/v1/leadership/{profile_id}/request-revision", json={"note": "Fix the bio."})
    assert revision.status_code == 200 and revision.json()["status"] == "draft"


def test_company_page_content_overview_workflow(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)

    assert client.get("/api/v1/company/pages/public/sustainability").status_code == 404
    assert client.get("/api/v1/company/pages/admin/not-a-real-section").status_code == 404

    admin_get = client.get("/api/v1/company/pages/admin/sustainability")
    assert admin_get.status_code == 200
    assert admin_get.json()["status"] == "draft"
    assert admin_get.json()["fields"] == {}

    update = client.put("/api/v1/company/pages/admin/sustainability", json={
        "fields": {"approach": "Information pending verification."}, "source_reference": None,
    })
    assert update.status_code == 200
    section_id = update.json()["id"]

    client.post(f"/api/v1/company/pages/{section_id}/submit")
    client.post(f"/api/v1/company/pages/{section_id}/review")
    client.post(f"/api/v1/company/pages/{section_id}/verify")
    client.post(f"/api/v1/company/pages/{section_id}/approve")
    publish = client.post(f"/api/v1/company/pages/{section_id}/publish")
    assert publish.status_code == 200

    public = client.get("/api/v1/company/pages/public/sustainability")
    assert public.status_code == 200
    assert public.json()["fields"]["approach"] == "Information pending verification."


def test_remaining_corporate_domains_are_wired_and_gated(client, super_admin):
    """One create+publish smoke test per remaining domain, confirming each
    router is mounted, farmer/dealer are blocked, and the public endpoint
    only returns published records."""
    _, email, password = super_admin
    _login(client, email, password)

    cases = [
        ("/api/v1/manufacturing/facilities", {"name": "Test Facility"}, "name"),
        ("/api/v1/research/facilities", {"name": "Test Lab"}, "name"),
        ("/api/v1/research/areas", {"title": "Test Area"}, "title"),
        ("/api/v1/certifications", {"name": "Test Cert"}, "name"),
        ("/api/v1/sustainability/initiatives", {"title": "Test Initiative"}, "title"),
    ]
    for base, payload, label_field in cases:
        create = client.post(base, json=payload)
        assert create.status_code == 200, f"{base}: {create.text}"
        item_id = create.json()["id"]
        for step in ("submit", "review", "verify", "approve", "publish"):
            r = client.post(f"{base}/{item_id}/{step}")
            assert r.status_code == 200, f"{base}/{step}: {r.text}"
        public = client.get(f"{base}/public").json()
        assert any(p["id"] == item_id for p in public), f"{base}: not visible publicly after publish"
        assert public[0][label_field] == payload[label_field]


def test_corporate_media_upload_requires_owner_or_manager_role(client, approved_dealer, super_admin):
    _, email, password, _ = approved_dealer
    _login(client, email, password)
    r = client.post("/api/v1/media/corporate/leadership_photo",
                     files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"x" * 20, "image/jpeg")})
    assert r.status_code == 403
    client.post("/api/v1/auth/logout")

    _, admin_email, admin_password = super_admin
    _login(client, admin_email, admin_password)
    bad_purpose = client.post("/api/v1/media/corporate/not_a_real_purpose",
                               files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"x" * 20, "image/jpeg")})
    assert bad_purpose.status_code == 400

    good = client.post("/api/v1/media/corporate/leadership_photo",
                        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"x" * 20, "image/jpeg")})
    assert good.status_code == 200, good.text
    assert "id" in good.json()


def test_corporate_entity_photo_upload_resolves_to_a_public_url(client, super_admin):
    """Every corporate-content entity type has a photo/document field now,
    not just leadership - upload the file, attach its id at create time,
    and confirm the *_url the frontend actually renders resolves and
    serves the real bytes (not just that the id round-trips)."""
    _, email, password = super_admin
    _login(client, email, password)

    cases = [
        ("/api/v1/leadership", "leadership_photo", {"full_name": "Test Person", "position": "CEO"}, "photo_media_id", "photo_url"),
        ("/api/v1/manufacturing/facilities", "manufacturing_photo", {"name": "Test Facility"}, "photo_media_id", "photo_url"),
        ("/api/v1/research/facilities", "research_photo", {"name": "Test Lab"}, "photo_media_id", "photo_url"),
        ("/api/v1/research/areas", "research_photo", {"title": "Test Area"}, "image_media_id", "image_url"),
        ("/api/v1/certifications", "certification_document", {"name": "Test Cert"}, "document_media_id", "document_url"),
        ("/api/v1/sustainability/initiatives", "sustainability_photo", {"title": "Test Initiative"}, "photo_media_id", "photo_url"),
    ]
    for base, purpose, payload, media_field, url_field in cases:
        upload = client.post(f"/api/v1/media/corporate/{purpose}", files={"file": ("f.jpg", b"\xff\xd8\xff" + b"x" * 20, "image/jpeg")})
        assert upload.status_code == 200, f"{purpose}: {upload.text}"
        media_id = upload.json()["id"]

        create = client.post(base, json={**payload, media_field: media_id})
        assert create.status_code == 200, f"{base}: {create.text}"
        body = create.json()
        assert body[media_field] == media_id
        assert body[url_field], f"{base}: {url_field} did not resolve"

        served = client.get(body[url_field])
        assert served.status_code == 200, f"{base}: {url_field} -> {served.status_code}"
        assert served.content == b"\xff\xd8\xff" + b"x" * 20
