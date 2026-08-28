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

    r = client.post(f"/api/v1/products/{pid}/transition/published", json={})
    assert r.status_code == 200

    r = client.get("/api/v1/products/public/neem-based-spray")
    assert r.status_code == 200

    r = client.post(f"/api/v1/products/{pid}/transition/unpublished", json={})
    assert r.status_code == 200
    assert client.get("/api/v1/products/public/neem-based-spray").status_code == 404

    r = client.post(f"/api/v1/products/{pid}/transition/archived", json={})
    assert r.status_code == 200


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
    assert r.status_code == 400  # missing category/description/precautions


def test_dealer_can_submit_a_product_listing_but_not_approve_or_publish_it(client, approved_dealer, super_admin):
    _, email, password, _ = approved_dealer
    _login(client, email, password)

    r = client.post("/api/v1/products", json={
        "sku": "SKU-DLR-001", "name": "Dealer Submitted Fertilizer", "slug": "dealer-submitted-fertilizer",
        "precautions": "Keep away from children.", "full_description": "Submitted by a dealer for review.",
    })
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    assert r.json()["status"] == "draft"

    # A dealer may edit their own draft...
    edit = client.put(f"/api/v1/products/{pid}", json={
        "sku": "SKU-DLR-001", "name": "Dealer Submitted Fertilizer (updated)", "slug": "dealer-submitted-fertilizer",
        "precautions": "Keep away from children.", "full_description": "Submitted by a dealer for review.",
    })
    assert edit.status_code == 200

    # ...and submit it for review...
    submit = client.post(f"/api/v1/products/{pid}/transition/in_review", json={})
    assert submit.status_code == 200
    assert submit.json()["status"] == "in_review"

    # ...but cannot approve, publish, or delete it themselves.
    assert client.post(f"/api/v1/products/{pid}/transition/approved", json={}).status_code == 403
    assert client.delete(f"/api/v1/products/{pid}").status_code == 403

    # nor edit it further once it's out of draft
    assert client.put(f"/api/v1/products/{pid}", json={
        "sku": "SKU-DLR-001", "name": "x", "slug": "dealer-submitted-fertilizer",
        "precautions": "x", "full_description": "x",
    }).status_code == 400

    # A real approver moves it to approved...
    client.post("/api/v1/auth/logout")
    _, admin_email, admin_password = super_admin
    _login(client, admin_email, admin_password)
    approve = client.post(f"/api/v1/products/{pid}/transition/approved", json={})
    assert approve.status_code == 200
    client.post("/api/v1/auth/logout")

    # ...but even now, the dealer still cannot publish their own approved listing.
    _login(client, email, password)
    assert client.post(f"/api/v1/products/{pid}/transition/published", json={}).status_code == 403


def test_dealer_cannot_see_or_modify_another_dealers_product(client, approved_dealer):
    from app.core.database import SessionLocal
    from app.core.permissions import ROLE_DEALER
    from tests.conftest import _make_user

    _, email, password, _ = approved_dealer
    other_uid, other_email, other_password = _make_user(ROLE_DEALER, "other-dealer@example.com")

    _login(client, other_email, other_password)
    other_product = client.post("/api/v1/products", json={
        "sku": "SKU-OTHER", "name": "Other Dealer Product", "slug": "other-dealer-product",
        "precautions": "x", "full_description": "x",
    }).json()
    client.post("/api/v1/auth/logout")

    _login(client, email, password)
    listing = client.get("/api/v1/products").json()
    assert all(item["id"] != other_product["id"] for item in listing["items"])

    forbidden_edit = client.put(f"/api/v1/products/{other_product['id']}", json={
        "sku": "SKU-OTHER", "name": "hijacked", "slug": "other-dealer-product",
        "precautions": "x", "full_description": "x",
    })
    assert forbidden_edit.status_code == 403


def test_farmer_cannot_create_a_product(client):
    client.post("/api/v1/auth/register", json={
        "full_name": "Product Farmer", "email": "productfarmer@example.com", "phone": "9876543260", "password": "Passw0rd123",
    })
    r = client.post("/api/v1/products", json={
        "sku": "SKU-FARM", "name": "Farmer Attempt", "slug": "farmer-attempt", "precautions": "x", "full_description": "x",
    })
    assert r.status_code == 403
