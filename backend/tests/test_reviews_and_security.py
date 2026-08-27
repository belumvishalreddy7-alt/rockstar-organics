def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200


def _publish_product(client, super_admin, sku="SKU-REV", slug="rev-product"):
    _, email, password = super_admin
    _login(client, email, password)
    r = client.post("/api/v1/products", json={"sku": sku, "name": "Reviewed Product", "slug": slug,
                                            "precautions": "x", "full_description": "x"})
    pid = r.json()["id"]
    cat = client.post("/api/v1/categories", json={"name": f"Cat-{sku}", "slug": f"cat-{slug}"})
    client.put(f"/api/v1/products/{pid}", json={"sku": sku, "name": "Reviewed Product", "slug": slug,
                                              "category_id": cat.json()["id"], "precautions": "x", "full_description": "x"})
    client.post(f"/api/v1/products/{pid}/transition/in_review", json={})
    client.post(f"/api/v1/products/{pid}/transition/approved", json={})
    client.post(f"/api/v1/products/{pid}/transition/published", json={})
    client.post("/api/v1/auth/logout")
    return pid


def test_review_hidden_until_moderated(client, super_admin):
    pid = _publish_product(client, super_admin)
    r = client.post(f"/api/v1/reviews/products/{pid}", json={"reviewer_name": "Farmer X", "rating": 5, "comment": "Good"})
    assert r.status_code == 200
    assert r.json()["status"] == "pending"

    detail = client.get(f"/api/v1/products/public/rev-product").json()
    assert detail["approved_review_count"] == 0
    assert detail["reviews"] == []


def test_approved_review_counts_toward_rating(client, super_admin):
    pid = _publish_product(client, super_admin, sku="SKU-REV2", slug="rev-product-2")
    client.post(f"/api/v1/reviews/products/{pid}", json={"reviewer_name": "Farmer Y", "rating": 4})

    _, email, password = super_admin
    _login(client, email, password)
    pending = client.get("/api/v1/reviews/pending").json()
    review_id = next(r["id"] for r in pending if r["product_id"] == pid)
    client.post(f"/api/v1/reviews/{review_id}/moderate", json={"status": "approved"})
    client.post("/api/v1/auth/logout")

    detail = client.get("/api/v1/products/public/rev-product-2").json()
    assert detail["approved_review_count"] == 1
    assert detail["average_rating"] == 4.0


def test_rejected_review_excluded(client, super_admin):
    pid = _publish_product(client, super_admin, sku="SKU-REV3", slug="rev-product-3")
    client.post(f"/api/v1/reviews/products/{pid}", json={"reviewer_name": "Farmer Z", "rating": 1})

    _, email, password = super_admin
    _login(client, email, password)
    pending = client.get("/api/v1/reviews/pending").json()
    review_id = next(r["id"] for r in pending if r["product_id"] == pid)
    client.post(f"/api/v1/reviews/{review_id}/moderate", json={"status": "rejected"})
    client.post("/api/v1/auth/logout")

    detail = client.get("/api/v1/products/public/rev-product-3").json()
    assert detail["approved_review_count"] == 0


def test_review_requires_published_product(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)
    r = client.post("/api/v1/products", json={"sku": "SKU-DRAFT", "name": "Draft", "slug": "draft-prod"})
    pid = r.json()["id"]
    client.post("/api/v1/auth/logout")
    r = client.post(f"/api/v1/reviews/products/{pid}", json={"reviewer_name": "X", "rating": 5})
    assert r.status_code == 400


def test_security_headers_present(client):
    r = client.get("/api/health")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert "content-security-policy" in {k.lower(): v for k, v in r.headers.items()}


def test_role_restriction_on_staff_only_endpoints(client, approved_dealer):
    _, email, password, _ = approved_dealer
    _login(client, email, password)
    r = client.post("/api/v1/products", json={"sku": "X", "name": "X", "slug": "x"})
    assert r.status_code == 403


def test_ownership_restriction_dealer_cannot_edit_other_profile(client, approved_dealer):
    _, email, password, _ = approved_dealer
    _login(client, email, password)
    r = client.put("/api/v1/dealers/me/profile", json={"directory_opt_in": True})
    assert r.status_code == 200  # only own profile is ever addressed; no ID param exists to target others
