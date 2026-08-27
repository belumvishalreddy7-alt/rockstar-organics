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
    cat = client.post("/api/v1/categories", params={"name": "Bio Pesticides", "slug": "bio-pesticides"})
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
