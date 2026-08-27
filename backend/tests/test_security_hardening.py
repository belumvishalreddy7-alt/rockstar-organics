"""Tests for the security hardening pass: CSRF double-submit protection,
session invalidation on password change, the change-password endpoint,
account status management, and input length caps."""


def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    return r


def test_csrf_token_required_for_mutating_request(client):
    client.post("/api/v1/auth/register", json={
        "full_name": "Csrf Farmer", "email": "csrffarmer@example.com", "phone": "9876543240", "password": "Passw0rd123",
    })
    assert client.cookies.get("rso_csrf") is not None

    # A request without the CSRF header (simulating a cross-site attacker
    # who has the ambient session cookie but cannot read its value) must
    # be rejected even though the session cookie is valid.
    import app.main as main_module
    from starlette.testclient import TestClient as PlainTestClient
    plain = PlainTestClient(main_module.app)
    plain.cookies.update(client.cookies)
    r = plain.post("/api/v1/cases", json={"title": "T", "description": "D", "district": "Hyderabad"})
    assert r.status_code == 403
    assert "csrf" in r.json()["detail"].lower()


def test_csrf_not_required_without_session(client):
    # Public, unauthenticated POST (no session cookie yet) must not require
    # a CSRF header - there's no session for CSRF to hijack.
    r = client.post("/api/v1/dealers/apply", json={
        "contact_person": "A", "business_name": "B", "email": "nocsrf@example.com", "phone": "9876543241",
        "district": "Hyderabad", "consent_given": True,
    })
    assert r.status_code == 200


def test_change_password_requires_current_password(client):
    client.post("/api/v1/auth/register", json={
        "full_name": "Change Pw", "email": "changepw@example.com", "phone": "9876543242", "password": "Passw0rd123",
    })
    r = client.post("/api/v1/auth/change-password", json={"current_password": "WrongPassword1", "new_password": "NewPassw0rd456"})
    assert r.status_code == 400

    r = client.post("/api/v1/auth/change-password", json={"current_password": "Passw0rd123", "new_password": "NewPassw0rd456"})
    assert r.status_code == 200


def test_password_change_invalidates_other_sessions(client):
    """Simulates a stolen session: session A is issued at login, then the
    password is changed from session B. Session A's token must stop
    working even though it hasn't expired."""
    client.post("/api/v1/auth/register", json={
        "full_name": "Session Farmer", "email": "sessionfarmer@example.com", "phone": "9876543243", "password": "Passw0rd123",
    })
    stolen_cookies = dict(client.cookies)

    r = client.post("/api/v1/auth/change-password", json={"current_password": "Passw0rd123", "new_password": "NewPassw0rd456"})
    assert r.status_code == 200

    import app.main as main_module
    from starlette.testclient import TestClient as PlainTestClient
    attacker = PlainTestClient(main_module.app)
    attacker.cookies.update(stolen_cookies)
    r = attacker.get("/api/v1/auth/me")
    assert r.json() is None  # old session token no longer resolves to a user


def test_suspended_farmer_account_via_accounts_endpoint(client, super_admin):
    _, admin_email, admin_password = super_admin
    client.post("/api/v1/auth/register", json={
        "full_name": "Suspend Target", "email": "suspendtarget@example.com", "phone": "9876543244", "password": "Passw0rd123",
    })
    client.post("/api/v1/auth/logout")

    _login(client, admin_email, admin_password)
    farmers = client.get("/api/v1/accounts/farmers").json()
    target = next(f for f in farmers if f["email"] == "suspendtarget@example.com")
    r = client.post(f"/api/v1/accounts/farmers/{target['id']}/status/suspended")
    assert r.status_code == 200
    client.post("/api/v1/auth/logout")

    r = client.post("/api/v1/auth/login", json={"email": "suspendtarget@example.com", "password": "Passw0rd123"})
    assert r.status_code == 401


def test_suspending_dealer_account_also_hides_from_directory(client, approved_dealer, sales_manager):
    uid, dealer_email, dealer_password, dealer_id = approved_dealer
    _, sm_email, sm_password = sales_manager
    _login(client, sm_email, sm_password)

    assert any(d["id"] == dealer_id for d in client.get("/api/v1/dealers/directory", params={"district": "Hyderabad"}).json())

    r = client.post(f"/api/v1/accounts/dealers/{uid}/status/suspended")
    assert r.status_code == 200

    assert not any(d["id"] == dealer_id for d in client.get("/api/v1/dealers/directory", params={"district": "Hyderabad"}).json())


def test_review_comment_length_is_capped(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)
    r = client.post("/api/v1/products", json={"sku": "SKU-CAP", "name": "Cap Product", "slug": "cap-product",
                                            "precautions": "x", "full_description": "x"})
    pid = r.json()["id"]
    cat = client.post("/api/v1/categories", json={"name": "Cap Cat", "slug": "cap-cat"})
    client.put(f"/api/v1/products/{pid}", json={"sku": "SKU-CAP", "name": "Cap Product", "slug": "cap-product",
                                              "category_id": cat.json()["id"], "precautions": "x", "full_description": "x"})
    client.post(f"/api/v1/products/{pid}/transition/in_review", json={})
    client.post(f"/api/v1/products/{pid}/transition/approved", json={})
    client.post(f"/api/v1/products/{pid}/transition/published", json={})
    client.post("/api/v1/auth/logout")

    huge_comment = "x" * 3000  # over the 2000-char cap
    r = client.post(f"/api/v1/reviews/products/{pid}", json={"reviewer_name": "Y", "rating": 5, "comment": huge_comment})
    assert r.status_code == 422


def test_enquiry_requires_explicit_consent(client):
    r = client.post("/api/v1/enquiries", json={
        "enquiry_type": "general", "name": "No Consent", "message": "Hello", "consent_given": False,
    })
    assert r.status_code == 422

    r = client.post("/api/v1/enquiries", json={
        "enquiry_type": "general", "name": "With Consent", "message": "Hello", "consent_given": True,
    })
    assert r.status_code == 200


def test_enquiry_with_blank_optional_email_is_accepted(client):
    # Regression test: the frontend Contact form submits email as "" (not
    # omitted) when the optional field is left blank. Pydantic's EmailStr
    # rejects "" outright unless the schema explicitly treats a blank
    # string the same as "not provided" - caught by an E2E Playwright run
    # against the real form, not by a unit test alone.
    r = client.post("/api/v1/enquiries", json={
        "enquiry_type": "general", "name": "Blank Email", "email": "",
        "message": "Hello", "consent_given": True,
    })
    assert r.status_code == 200, r.text
    assert r.json()["reference_number"]


def test_change_password_is_rate_limited(client):
    """Guards a hijacked session from grinding through current_password
    guesses (each of which costs a real Argon2 verification server-side)."""
    client.post("/api/v1/auth/register", json={
        "full_name": "Rate Change Pw", "email": "ratechangepw@example.com", "phone": "9876543246", "password": "Passw0rd123",
    })
    for _ in range(5):
        r = client.post("/api/v1/auth/change-password", json={"current_password": "WrongPassword1", "new_password": "NewPassw0rd456"})
        assert r.status_code == 400
    r = client.post("/api/v1/auth/change-password", json={"current_password": "WrongPassword1", "new_password": "NewPassw0rd456"})
    assert r.status_code == 429


def test_reset_password_is_rate_limited(client):
    for _ in range(10):
        r = client.post("/api/v1/auth/reset-password", json={"token": "not-a-real-token", "new_password": "Passw0rd123"})
        assert r.status_code == 400
    r = client.post("/api/v1/auth/reset-password", json={"token": "not-a-real-token", "new_password": "Passw0rd123"})
    assert r.status_code == 429


def test_password_max_length_enforced(client):
    # Rejected at the schema layer (422) since Field(max_length=...) catches
    # it before password_strength_errors ever runs - either way, an
    # oversized password never reaches Argon2 hashing.
    huge_password = "Aa1" + ("x" * 300)
    r = client.post("/api/v1/auth/register", json={
        "full_name": "Huge Pw", "email": "hugepw@example.com", "phone": "9876543245", "password": huge_password,
    })
    assert r.status_code == 422
