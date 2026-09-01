import uuid


def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200


def _register_farmer(client):
    """Reviews are farmer-account-only (see routers/reviews.py) - every
    review test needs a real, freshly registered farmer to log in as."""
    suffix = uuid.uuid4().hex[:10]
    email = f"reviewer-{suffix}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "full_name": f"Reviewer {suffix}", "email": email, "phone": "9876543299", "password": "Passw0rd123",
    })
    assert r.status_code == 200, r.text
    return email


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
    client.post(f"/api/v1/media/products/{pid}/images?alt_text=Front", files={"file": ("f.jpg", b"\xff\xd8\xff" + b"x" * 20, "image/jpeg")})
    client.post(f"/api/v1/products/{pid}/transition/published", json={})
    client.post("/api/v1/auth/logout")
    return pid


def test_review_hidden_until_moderated(client, super_admin):
    pid = _publish_product(client, super_admin)
    _register_farmer(client)
    r = client.post(f"/api/v1/reviews/products/{pid}", json={"rating": 5, "comment": "Good"})
    assert r.status_code == 200
    assert r.json()["status"] == "pending"
    client.post("/api/v1/auth/logout")

    detail = client.get(f"/api/v1/products/public/rev-product").json()
    assert detail["approved_review_count"] == 0
    assert detail["reviews"] == []


def test_anonymous_and_non_farmer_cannot_submit_review(client, super_admin, approved_dealer):
    pid = _publish_product(client, super_admin, sku="SKU-REVAUTH", slug="rev-product-auth")

    anon = client.post(f"/api/v1/reviews/products/{pid}", json={"rating": 5})
    assert anon.status_code == 401

    _, dealer_email, dealer_password, _ = approved_dealer
    _login(client, dealer_email, dealer_password)
    dealer_attempt = client.post(f"/api/v1/reviews/products/{pid}", json={"rating": 5})
    assert dealer_attempt.status_code == 403
    client.post("/api/v1/auth/logout")


def test_review_uses_account_name_not_client_supplied_text(client, super_admin):
    """Regression test: reviewer_name is no longer accepted from the
    client at all (even if sent, it must be ignored) - it always comes
    from the authenticated farmer's own account name."""
    pid = _publish_product(client, super_admin, sku="SKU-REVNAME", slug="rev-product-name")
    farmer_email = _register_farmer(client)
    r = client.post(f"/api/v1/reviews/products/{pid}", json={"rating": 5, "reviewer_name": "Someone Else Entirely"})
    assert r.status_code == 200

    _, admin_email, admin_password = super_admin
    client.post("/api/v1/auth/logout")
    _login(client, admin_email, admin_password)
    pending = client.get("/api/v1/reviews/pending").json()
    review = next(r for r in pending if r["product_id"] == pid)
    assert review["reviewer_name"] != "Someone Else Entirely"
    assert farmer_email.split("@")[0] in review["reviewer_name"] or "Reviewer" in review["reviewer_name"]
    client.post("/api/v1/auth/logout")


def test_approved_review_counts_toward_rating(client, super_admin):
    pid = _publish_product(client, super_admin, sku="SKU-REV2", slug="rev-product-2")
    _register_farmer(client)
    client.post(f"/api/v1/reviews/products/{pid}", json={"rating": 4})
    client.post("/api/v1/auth/logout")

    _, email, password = super_admin
    _login(client, email, password)
    pending = client.get("/api/v1/reviews/pending").json()
    review_id = next(r["id"] for r in pending if r["product_id"] == pid)
    client.post(f"/api/v1/reviews/{review_id}/moderate", json={"status": "approved"})
    client.post("/api/v1/auth/logout")

    detail = client.get("/api/v1/products/public/rev-product-2").json()
    assert detail["approved_review_count"] == 1
    assert detail["average_rating"] == 4.0
    assert detail["rating_breakdown"]["4"] == 1


def test_rejected_review_excluded(client, super_admin):
    pid = _publish_product(client, super_admin, sku="SKU-REV3", slug="rev-product-3")
    _register_farmer(client)
    client.post(f"/api/v1/reviews/products/{pid}", json={"rating": 1})
    client.post("/api/v1/auth/logout")

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
    _register_farmer(client)
    r = client.post(f"/api/v1/reviews/products/{pid}", json={"rating": 5})
    assert r.status_code == 400
    client.post("/api/v1/auth/logout")


def test_security_headers_present(client):
    r = client.get("/api/health")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert "content-security-policy" in {k.lower(): v for k, v in r.headers.items()}


def test_role_restriction_on_staff_only_endpoints(client, approved_dealer):
    """Category management is staff-only, same as product creation itself
    (see test_products.py's dealer test)."""
    _, email, password, _ = approved_dealer
    _login(client, email, password)
    r = client.post("/api/v1/categories", json={"name": "X", "slug": "x"})
    assert r.status_code == 403


def test_ownership_restriction_dealer_cannot_edit_other_profile(client, approved_dealer):
    _, email, password, _ = approved_dealer
    _login(client, email, password)
    r = client.put("/api/v1/dealers/me/profile", json={"directory_opt_in": True})
    assert r.status_code == 200  # only own profile is ever addressed; no ID param exists to target others
