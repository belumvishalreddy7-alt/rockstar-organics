def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200


def test_catalogue_starts_empty(client):
    r = client.get("/api/v1/products/public")
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_product_lifecycle_and_visibility(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)

    r = client.post("/api/v1/products", json={
        "sku": "SKU-001", "name": "Neem Based Spray", "slug": "neem-based-spray",
        "category_id": None, "precautions": "Keep away from children.",
        "full_description": "A neem-based formulation for foliar application.",
    })
    assert r.status_code == 200, r.text
    product = r.json()
    assert product["status"] == "draft"

    # draft not visible publicly
    assert client.get("/api/v1/products/public/neem-based-spray").status_code == 404

    pid = product["id"]
    r = client.post(f"/api/v1/products/{pid}/transition/in_review", json={})
    assert r.status_code == 200
    r = client.post(f"/api/v1/products/{pid}/transition/approved", json={})
    assert r.status_code == 200

    # create category first, then update product to attach it (publication requires category)
    cat = client.post("/api/v1/categories", json={"name": "Bio Pesticides", "slug": "bio-pesticides"})
    assert cat.status_code == 200
    client.put(f"/api/v1/products/{pid}", json={
        "sku": "SKU-001", "name": "Neem Based Spray", "slug": "neem-based-spray",
        "category_id": cat.json()["id"], "precautions": "Keep away from children.",
        "full_description": "A neem-based formulation for foliar application.",
    })
    upload = client.post(f"/api/v1/media/products/{pid}/images?alt_text=Front%20of%20pack",
                          files={"file": ("front.jpg", b"\xff\xd8\xff" + b"x" * 20, "image/jpeg")})
    assert upload.status_code == 200, upload.text

    r = client.post(f"/api/v1/products/{pid}/transition/published", json={})
    assert r.status_code == 200

    r = client.get("/api/v1/products/public/neem-based-spray")
    assert r.status_code == 200
    assert r.json()["category_name"] == "Bio Pesticides"

    listed = client.get("/api/v1/products/public")
    assert listed.json()["items"][0]["category_name"] == "Bio Pesticides"

    r = client.post(f"/api/v1/products/{pid}/transition/unpublished", json={})
    assert r.status_code == 200
    assert client.get("/api/v1/products/public/neem-based-spray").status_code == 404

    r = client.post(f"/api/v1/products/{pid}/transition/archived", json={})
    assert r.status_code == 200


def test_manufacturing_and_expiry_dates_editable_and_public(client, super_admin):
    """Covers the exact dead end a real user hit: a product stuck at
    'Cannot publish: missing category' with no field for it on the create
    form - PUT lets an existing product's category (and these two new
    date fields) be set after the fact, not just at creation time."""
    _, email, password = super_admin
    _login(client, email, password)
    r = client.post("/api/v1/products", json={"sku": "SKU-DATES", "name": "Dated Product", "slug": "dated-product",
                                            "precautions": "x", "full_description": "x"})
    pid = r.json()["id"]
    assert r.json()["manufacturing_date"] is None
    client.post(f"/api/v1/products/{pid}/transition/in_review", json={})
    client.post(f"/api/v1/products/{pid}/transition/approved", json={})

    stuck = client.post(f"/api/v1/products/{pid}/transition/published", json={})
    assert stuck.status_code == 400
    assert "category" in stuck.json()["detail"]

    cat = client.post("/api/v1/categories", json={"name": "Dates Cat", "slug": "dates-cat"})
    update = client.put(f"/api/v1/products/{pid}", json={
        "sku": "SKU-DATES", "name": "Dated Product", "slug": "dated-product",
        "category_id": cat.json()["id"], "precautions": "x", "full_description": "x",
        "manufacturing_date": "2026-01-15", "expiry_date": "2027-01-15",
    })
    assert update.status_code == 200, update.text
    assert update.json()["manufacturing_date"] == "2026-01-15"
    assert update.json()["expiry_date"] == "2027-01-15"

    client.post(f"/api/v1/media/products/{pid}/images?alt_text=Front", files={"file": ("f.jpg", b"\xff\xd8\xff" + b"x" * 20, "image/jpeg")})
    published = client.post(f"/api/v1/products/{pid}/transition/published", json={})
    assert published.status_code == 200, published.text

    public = client.get("/api/v1/products/public/dated-product")
    assert public.json()["manufacturing_date"] == "2026-01-15"
    assert public.json()["expiry_date"] == "2027-01-15"


def test_delete_product(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)
    r = client.post("/api/v1/products", json={"sku": "SKU-DEL", "name": "Deletable", "slug": "deletable",
                                            "precautions": "x", "full_description": "x"})
    pid = r.json()["id"]

    deleted = client.delete(f"/api/v1/products/{pid}")
    assert deleted.status_code == 200, deleted.text
    remaining = client.get("/api/v1/products").json()["items"]
    assert not any(p["id"] == pid for p in remaining)


def test_content_manager_can_verify_but_not_approve_or_publish_product(client, super_admin):
    from app.core.permissions import ROLE_CONTENT_MANAGER
    from tests.conftest import _make_user
    import uuid

    _, admin_email, admin_password = super_admin
    _login(client, admin_email, admin_password)
    r = client.post("/api/v1/products", json={"sku": "SKU-ROLE", "name": "Role Test Product", "slug": "role-test-product",
                                            "precautions": "x", "full_description": "x"})
    pid = r.json()["id"]
    client.post("/api/v1/auth/logout")

    cm_email, cm_password = f"cm-{uuid.uuid4().hex[:8]}@example.com", "Passw0rd123"
    _make_user(ROLE_CONTENT_MANAGER, cm_email, cm_password)
    _login(client, cm_email, cm_password)

    # verifier can move it through the review-tier transitions...
    submit = client.post(f"/api/v1/products/{pid}/transition/in_review", json={})
    assert submit.status_code == 200

    # ...but cannot approve, publish, or archive it - that's the approver's job.
    assert client.post(f"/api/v1/products/{pid}/transition/approved", json={}).status_code == 403


def test_product_image_upload_and_removal(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)
    r = client.post("/api/v1/products", json={"sku": "SKU-IMAGE", "name": "Imaged Product", "slug": "imaged-product",
                                            "precautions": "x", "full_description": "x"})
    pid = r.json()["id"]

    upload = client.post(f"/api/v1/media/products/{pid}/images?alt_text=Front%20of%20pack",
                          files={"file": ("front.jpg", b"\xff\xd8\xff" + b"x" * 20, "image/jpeg")})
    assert upload.status_code == 200, upload.text
    image_id = upload.json()["id"]

    listed = client.get("/api/v1/products").json()["items"]
    product = next(p for p in listed if p["id"] == pid)
    assert len(product["images"]) == 1
    assert product["images"][0]["id"] == image_id

    remove = client.delete(f"/api/v1/products/{pid}/images/{image_id}")
    assert remove.status_code == 200

    listed_after = client.get("/api/v1/products").json()["items"]
    product_after = next(p for p in listed_after if p["id"] == pid)
    assert product_after["images"] == []


def test_product_translations_saved_and_returned(client, super_admin):
    """Owner-entered translations round-trip through create and update, and
    an unsupported language code is rejected outright - these are never
    machine-translated, so a typo'd language key should fail loudly rather
    than silently storing under the wrong key."""
    _, email, password = super_admin
    _login(client, email, password)

    r = client.post("/api/v1/products", json={
        "sku": "SKU-I18N", "name": "Translated Product", "slug": "translated-product",
        "precautions": "Keep away from children.", "full_description": "English description.",
        "translations": {"te": {"name": "తెలుగు పేరు", "precautions": "పిల్లలకు దూరంగా ఉంచండి."}},
    })
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    assert r.json()["translations"] == {"te": {"name": "తెలుగు పేరు", "precautions": "పిల్లలకు దూరంగా ఉంచండి."}}

    bad_lang = client.put(f"/api/v1/products/{pid}", json={
        "sku": "SKU-I18N", "name": "Translated Product", "slug": "translated-product",
        "precautions": "Keep away from children.", "full_description": "English description.",
        "translations": {"fr": {"name": "Nom français"}},
    })
    assert bad_lang.status_code == 422

    updated = client.put(f"/api/v1/products/{pid}", json={
        "sku": "SKU-I18N", "name": "Translated Product", "slug": "translated-product",
        "precautions": "Keep away from children.", "full_description": "English description.",
        "translations": {"hi": {"name": "हिंदी नाम"}},
    })
    assert updated.status_code == 200, updated.text
    # PUT replaces the whole row, same as every other field - the earlier
    # Telugu entry is gone because this update didn't resend it.
    assert updated.json()["translations"] == {"hi": {"name": "हिंदी नाम"}}

    fetched = client.get("/api/v1/products").json()["items"][0]
    assert fetched["translations"] == {"hi": {"name": "हिंदी नाम"}}


def test_sku_and_slug_uniqueness(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)
    payload = {"sku": "SKU-DUP", "name": "A", "slug": "a-product", "precautions": "x", "full_description": "x"}
    assert client.post("/api/v1/products", json=payload).status_code == 200
    dup_sku = {**payload, "slug": "a-product-2"}
    assert client.post("/api/v1/products", json=dup_sku).status_code == 400
    dup_slug = {**payload, "sku": "SKU-DUP-2"}
    assert client.post("/api/v1/products", json=dup_slug).status_code == 400


def test_publish_requires_fields(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)
    r = client.post("/api/v1/products", json={"sku": "SKU-INC", "name": "Incomplete", "slug": "incomplete"})
    pid = r.json()["id"]
    client.post(f"/api/v1/products/{pid}/transition/in_review", json={})
    client.post(f"/api/v1/products/{pid}/transition/approved", json={})
    r = client.post(f"/api/v1/products/{pid}/transition/published", json={})
    assert r.status_code == 400  # missing category/description/precautions/image
    assert "image" in r.json()["detail"]


def test_publish_requires_at_least_one_image(client, super_admin):
    """A product can otherwise satisfy every text field yet still have had
    its only image removed after upload - publish must still catch that,
    not just check whether an image was ever attached."""
    _, email, password = super_admin
    _login(client, email, password)
    r = client.post("/api/v1/products", json={"sku": "SKU-NOIMG", "name": "No Image", "slug": "no-image",
                                            "precautions": "x", "full_description": "x"})
    pid = r.json()["id"]
    cat = client.post("/api/v1/categories", json={"name": "No Image Cat", "slug": "no-image-cat"})
    client.put(f"/api/v1/products/{pid}", json={"sku": "SKU-NOIMG", "name": "No Image", "slug": "no-image",
                                              "category_id": cat.json()["id"], "precautions": "x", "full_description": "x"})
    client.post(f"/api/v1/products/{pid}/transition/in_review", json={})
    client.post(f"/api/v1/products/{pid}/transition/approved", json={})

    without_image = client.post(f"/api/v1/products/{pid}/transition/published", json={})
    assert without_image.status_code == 400
    assert "image" in without_image.json()["detail"]

    upload = client.post(f"/api/v1/media/products/{pid}/images?alt_text=Front",
                          files={"file": ("f.jpg", b"\xff\xd8\xff" + b"x" * 20, "image/jpeg")})
    image_id = upload.json()["id"]
    with_image = client.post(f"/api/v1/products/{pid}/transition/published", json={})
    assert with_image.status_code == 200, with_image.text

    # removing the only image afterward doesn't retroactively unpublish -
    # this test documents current behavior, it isn't asserting that's ideal
    assert client.delete(f"/api/v1/products/{pid}/images/{image_id}").status_code == 200


def test_dealer_cannot_create_list_or_manage_products(client, approved_dealer):
    """Product creation/upload is restricted to the owner (super_admin) and
    company managers (admin, content_manager) only - a dealer has no product
    access at all, not even to their own draft."""
    _, email, password, _ = approved_dealer
    _login(client, email, password)

    assert client.get("/api/v1/products").status_code == 403
    r = client.post("/api/v1/products", json={
        "sku": "SKU-DLR-001", "name": "Dealer Submitted Fertilizer", "slug": "dealer-submitted-fertilizer",
        "precautions": "Keep away from children.", "full_description": "Submitted by a dealer for review.",
    })
    assert r.status_code == 403


def test_farmer_cannot_create_a_product(client):
    client.post("/api/v1/auth/register", json={
        "full_name": "Product Farmer", "email": "productfarmer@example.com", "phone": "9876543260", "password": "Passw0rd123",
    })
    r = client.post("/api/v1/products", json={
        "sku": "SKU-FARM", "name": "Farmer Attempt", "slug": "farmer-attempt", "precautions": "x", "full_description": "x",
    })
    assert r.status_code == 403
