"""Tests for the 2026-08-28 product management extension: structured pack
sizes/crops/claims/certifications/documents, and the verifier/approver role
split (content_manager can move a product through verification but only
super_admin/admin can approve, publish, or archive it)."""
import uuid


def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200


def _create_draft_product(client, sku="SKU-EXT-001"):
    r = client.post("/api/v1/products", json={
        "sku": sku, "name": "Extension Test Product", "slug": f"extension-test-{sku.lower()}",
        "precautions": "Keep away from children.", "full_description": "A product for testing the CMS extensions.",
    })
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_pack_sizes_and_crops_can_be_added_and_removed(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)
    pid = _create_draft_product(client)

    ps = client.post(f"/api/v1/products/{pid}/pack-sizes", json={"quantity": "500", "unit": "g", "packaging_type": "bottle"})
    assert ps.status_code == 200, ps.text
    ps_id = ps.json()["id"]
    assert client.get("/api/v1/products").json()["items"][0]["pack_size_records"][0]["quantity"] == "500"

    crop = client.post(f"/api/v1/products/{pid}/crops", json={"crop_name": "Paddy", "application_stage": "Flowering"})
    assert crop.status_code == 200, crop.text

    assert client.delete(f"/api/v1/products/{pid}/pack-sizes/{ps_id}").status_code == 200
    remaining = client.get("/api/v1/products").json()["items"][0]["pack_size_records"]
    assert remaining == []


def test_claim_is_hidden_publicly_until_verified(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)
    pid = _create_draft_product(client, sku="SKU-EXT-CLAIM")

    claim = client.post(f"/api/v1/products/{pid}/claims", json={"claim_text": "Improves soil health.", "category": "benefit"})
    assert claim.status_code == 200, claim.text
    claim_id = claim.json()["id"]
    assert claim.json()["verification_status"] == "pending"

    # publish the product so the public endpoint would serve it at all
    client.post(f"/api/v1/products/{pid}/transition/in_review", json={})
    client.post(f"/api/v1/products/{pid}/transition/approved", json={})
    cat = client.post("/api/v1/categories", json={"name": f"Ext Cat {uuid.uuid4().hex[:6]}", "slug": f"ext-cat-{uuid.uuid4().hex[:6]}"})
    client.put(f"/api/v1/products/{pid}", json={
        "sku": "SKU-EXT-CLAIM", "name": "Extension Test Product", "slug": "extension-test-sku-ext-claim",
        "category_id": cat.json()["id"], "precautions": "Keep away from children.", "full_description": "desc",
    })
    publish = client.post(f"/api/v1/products/{pid}/transition/published", json={})
    assert publish.status_code == 200, publish.text

    public = client.get("/api/v1/products/public/extension-test-sku-ext-claim")
    assert public.status_code == 200
    assert public.json()["claims"] == []  # unverified claim never leaks publicly

    verify = client.post(f"/api/v1/products/{pid}/claims/{claim_id}/verify", json={"verification_status": "verified"})
    assert verify.status_code == 200

    public_after = client.get("/api/v1/products/public/extension-test-sku-ext-claim")
    assert len(public_after.json()["claims"]) == 1
    assert public_after.json()["claims"][0]["claim_text"] == "Improves soil health."


def test_content_manager_can_verify_but_not_approve_or_publish_product(client, super_admin):
    from app.core.permissions import ROLE_CONTENT_MANAGER
    from tests.conftest import _make_user

    _, admin_email, admin_password = super_admin
    _login(client, admin_email, admin_password)
    pid = _create_draft_product(client, sku="SKU-EXT-ROLE")
    client.post("/api/v1/auth/logout")

    cm_email, cm_password = f"cm-{uuid.uuid4().hex[:8]}@example.com", "Passw0rd123"
    _make_user(ROLE_CONTENT_MANAGER, cm_email, cm_password)
    _login(client, cm_email, cm_password)

    # verifier can move it through the review-tier transitions...
    submit = client.post(f"/api/v1/products/{pid}/transition/in_review", json={})
    assert submit.status_code == 200

    # ...but cannot approve, publish, or archive it - that's the approver's job.
    assert client.post(f"/api/v1/products/{pid}/transition/approved", json={}).status_code == 403


def test_document_upload_and_verification_flow(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)
    pid = _create_draft_product(client, sku="SKU-EXT-DOC")

    upload = client.post(f"/api/v1/media/products/{pid}/documents", files={"file": ("tds.pdf", b"%PDF-1.4 x", "application/pdf")})
    assert upload.status_code == 200, upload.text
    media_id = upload.json()["id"]

    doc = client.post(f"/api/v1/products/{pid}/documents", json={
        "document_type": "technical_data_sheet", "title": "Technical Data Sheet", "media_id": media_id,
    })
    assert doc.status_code == 200, doc.text
    doc_id = doc.json()["id"]
    assert doc.json()["verification_status"] == "pending"

    verify = client.post(f"/api/v1/products/{pid}/documents/{doc_id}/verify", json={"verification_status": "verified"})
    assert verify.status_code == 200
    assert verify.json()["verification_status"] == "verified"


def test_dealer_has_no_product_access(client, approved_dealer, super_admin):
    """Product creation/upload is owner (super_admin) + manager
    (admin, content_manager) only - a dealer cannot create a product, add a
    claim to one, or verify a claim."""
    admin_uid, admin_email, admin_password = super_admin
    _login(client, admin_email, admin_password)
    pid = _create_draft_product(client, sku="SKU-EXT-DEALER-CLAIM")
    claim = client.post(f"/api/v1/products/{pid}/claims", json={"claim_text": "Boosts yield.", "category": "benefit"})
    claim_id = claim.json()["id"]
    client.post("/api/v1/auth/logout")

    _, email, password, _ = approved_dealer
    _login(client, email, password)
    assert client.post("/api/v1/products", json={
        "sku": "SKU-EXT-DEALER-002", "name": "x", "slug": "ext-dealer-002",
        "precautions": "x", "full_description": "x",
    }).status_code == 403
    assert client.post(f"/api/v1/products/{pid}/claims", json={"claim_text": "x", "category": "benefit"}).status_code == 403
    # only a verifier (content_manager/admin/super_admin) may verify a claim
    assert client.post(f"/api/v1/products/{pid}/claims/{claim_id}/verify", json={"verification_status": "verified"}).status_code == 403
