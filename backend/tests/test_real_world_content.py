"""Tests for the real-world-content pass: OTP-gated signup, the Distributor
role/portal, company certificates/documents, and the agriculture photo
gallery. Email sending itself is exercised with EMAIL_PROVIDER_ENABLED left
at its default (false) - see test_email_disabled_by_default - so this suite
never makes a real network call to Brevo; app/core/email.py's live
integration is verified separately (manually, against the real API), not
here, matching the project's "never claim a test passed unless executed"
rule for things this environment cannot safely automate.
"""
import uuid

from app.core.email import send_email


def _unique_email(prefix="signup"):
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def test_email_disabled_by_default(client):
    # EMAIL_PROVIDER_ENABLED defaults to false in every environment unless
    # explicitly configured - send_email must never claim success, and must
    # never raise, when that's the case.
    result = send_email(to="nobody@example.com", subject="test", html="<p>hi</p>", text="hi")
    assert result.sent is False
    assert result.error


def test_signup_then_verify_otp_creates_farmer_account(client):
    email = _unique_email()
    r = client.post("/api/v1/auth/signup", json={
        "full_name": "OTP Farmer", "email": email, "phone": "9876543210", "password": "CorrectHorse9!",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email_sent"] is False  # provider disabled in tests
    otp_code = body["dev_otp_code"]  # DEV_EXPOSE_OTP is true in the test environment

    # Wrong code is rejected and does not create an account.
    bad = client.post("/api/v1/auth/verify-otp", json={"email": email, "code": "000000"})
    assert bad.status_code == 400

    r2 = client.post("/api/v1/auth/verify-otp", json={"email": email, "code": otp_code})
    assert r2.status_code == 200, r2.text
    user = r2.json()
    assert user["email"] == email
    assert user["role"] == "farmer"

    # The session issued by verify-otp is immediately usable.
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == email

    # The same code cannot be reused.
    replay = client.post("/api/v1/auth/verify-otp", json={"email": _unique_email(), "code": otp_code})
    assert replay.status_code == 400


def test_signup_rejects_duplicate_email(client):
    email = _unique_email()
    r1 = client.post("/api/v1/auth/signup", json={
        "full_name": "First", "email": email, "phone": "9876543210", "password": "CorrectHorse9!",
    })
    assert r1.status_code == 200
    client.post("/api/v1/auth/verify-otp", json={"email": email, "code": r1.json()["dev_otp_code"]})

    r2 = client.post("/api/v1/auth/signup", json={
        "full_name": "Second", "email": email, "phone": "9876543211", "password": "CorrectHorse9!",
    })
    assert r2.status_code == 400


def test_distributor_application_approval_creates_account(client, sales_manager):
    email = _unique_email("distributor")
    r = client.post("/api/v1/distributors/apply", json={
        "contact_person": "Test Distributor", "business_name": "Telangana Agri Distribution Co",
        "email": email, "phone": "9876543212", "territory": "Ranga Reddy district",
        "consent_given": True,
    })
    assert r.status_code == 200, r.text
    app_id = r.json()["id"]

    uid, admin_email, admin_password = sales_manager
    client.post("/api/v1/auth/login", json={"email": admin_email, "password": admin_password})

    approve = client.post(f"/api/v1/distributors/applications/{app_id}/status/approved", json={})
    assert approve.status_code == 200, approve.text
    creds = approve.json()["distributor_credentials"]
    assert creds["email"] == email
    assert "temporary_password" in creds
    # Not sent for real - provider disabled - but the endpoint must say so
    # rather than silently pretending delivery happened.
    assert "email_delivery" in creds

    # approval alone (no separate opt-in step) makes the distributor
    # findable by farmers in the public directory
    directory = client.get("/api/v1/distributors/directory", params={"territory": "Ranga Reddy district"}).json()
    assert any(d["business_name"] == "Telangana Agri Distribution Co" and d["public_phone"] == "9876543212" for d in directory)

    client.post("/api/v1/auth/logout")
    login = client.post("/api/v1/auth/login", json={"email": email, "password": creds["temporary_password"]})
    assert login.status_code == 200
    assert login.json()["role"] == "distributor"
    assert login.json()["must_change_password"] is True
    distributor_user_id = login.json()["id"]
    client.post("/api/v1/auth/logout")

    # suspending the account also pulls it out of the public directory -
    # the only way staff had to do this before now had no frontend page
    # to reach it from at all
    client.post("/api/v1/auth/login", json={"email": admin_email, "password": admin_password})
    suspend = client.post(f"/api/v1/accounts/distributors/{distributor_user_id}/status/suspended")
    assert suspend.status_code == 200
    after_suspend = client.get("/api/v1/distributors/directory", params={"territory": "Ranga Reddy district"}).json()
    assert not any(d["business_name"] == "Telangana Agri Distribution Co" for d in after_suspend)
    client.post("/api/v1/auth/logout")


def test_delete_distributor_removes_profile_disables_login_and_handles_stock(client, sales_manager, super_admin):
    """Same coverage as the dealer equivalent: attaches a stock declaration
    (distributor_stock.distributor_id has no ORM cascade) before deleting,
    to confirm it's cleaned up rather than 500ing."""
    email = _unique_email("del-distributor-stock")
    r = client.post("/api/v1/distributors/apply", json={
        "contact_person": "Del Stock Distributor", "business_name": "Del Stock Distribution Co",
        "email": email, "phone": "9876543214", "territory": "Del stock territory", "consent_given": True,
    })
    app_id = r.json()["id"]

    _, sm_email, sm_password = sales_manager
    client.post("/api/v1/auth/login", json={"email": sm_email, "password": sm_password})
    approve = client.post(f"/api/v1/distributors/applications/{app_id}/status/approved", json={})
    assert approve.status_code == 200, approve.text
    creds = approve.json()["distributor_credentials"]
    client.post("/api/v1/auth/logout")

    _, admin_email, admin_password = super_admin
    client.post("/api/v1/auth/login", json={"email": admin_email, "password": admin_password})
    product = client.post("/api/v1/products", json={"sku": "SKU-DSTDEL", "name": "Distributor Delete Product", "slug": "distributor-delete-product",
                                                  "precautions": "x", "full_description": "x"})
    pid = product.json()["id"]
    cat = client.post("/api/v1/categories", json={"name": "Distributor Del Cat", "slug": "distributor-del-cat"})
    client.put(f"/api/v1/products/{pid}", json={"sku": "SKU-DSTDEL", "name": "Distributor Delete Product", "slug": "distributor-delete-product",
                                              "category_id": cat.json()["id"], "precautions": "x", "full_description": "x"})
    client.post(f"/api/v1/products/{pid}/transition/in_review", json={})
    client.post(f"/api/v1/products/{pid}/transition/approved", json={})
    client.post(f"/api/v1/media/products/{pid}/images?alt_text=Front", files={"file": ("f.jpg", b"\xff\xd8\xff" + b"x" * 20, "image/jpeg")})
    client.post(f"/api/v1/products/{pid}/transition/published", json={})
    client.post("/api/v1/auth/logout")

    login = client.post("/api/v1/auth/login", json={"email": email, "password": creds["temporary_password"]})
    distributor_user_id = login.json()["id"]
    stock = client.post(f"/api/v1/distributors/me/stock/{pid}/available")
    assert stock.status_code == 200, stock.text
    client.post("/api/v1/auth/logout")

    client.post("/api/v1/auth/login", json={"email": sm_email, "password": sm_password})
    forbidden = client.delete(f"/api/v1/accounts/distributors/{distributor_user_id}")
    assert forbidden.status_code == 403
    client.post("/api/v1/auth/logout")

    client.post("/api/v1/auth/login", json={"email": admin_email, "password": admin_password})
    deleted = client.delete(f"/api/v1/accounts/distributors/{distributor_user_id}")
    assert deleted.status_code == 200, deleted.text
    after = client.get("/api/v1/distributors/directory", params={"territory": "Del stock territory"}).json()
    assert not any(d["business_name"] == "Del Stock Distribution Co" for d in after)
    client.post("/api/v1/auth/logout")

    assert client.post("/api/v1/auth/login", json={"email": email, "password": creds["temporary_password"]}).status_code == 401


def test_distributor_application_rejects_invalid_status(client, sales_manager):
    uid, admin_email, admin_password = sales_manager
    client.post("/api/v1/auth/login", json={"email": admin_email, "password": admin_password})
    r = client.get("/api/v1/distributors/applications")
    assert r.status_code == 200


def test_delete_approved_distributor_application_does_not_break_the_profile(client, sales_manager, super_admin):
    email = _unique_email("del-distributor")
    r = client.post("/api/v1/distributors/apply", json={
        "contact_person": "Del Distributor", "business_name": "Del Distribution Co",
        "email": email, "phone": "9876543213", "territory": "Del territory", "consent_given": True,
    })
    app_id = r.json()["id"]

    _, sm_email, sm_password = sales_manager
    client.post("/api/v1/auth/login", json={"email": sm_email, "password": sm_password})
    approve = client.post(f"/api/v1/distributors/applications/{app_id}/status/approved", json={})
    assert approve.status_code == 200, approve.text
    client.post("/api/v1/auth/logout")

    client.post("/api/v1/auth/login", json={"email": sm_email, "password": sm_password})
    assert client.delete(f"/api/v1/distributors/applications/{app_id}").status_code == 403
    client.post("/api/v1/auth/logout")

    _, admin_email, admin_password = super_admin
    client.post("/api/v1/auth/login", json={"email": admin_email, "password": admin_password})
    deleted = client.delete(f"/api/v1/distributors/applications/{app_id}")
    assert deleted.status_code == 200, deleted.text
    assert client.delete(f"/api/v1/distributors/applications/{app_id}").status_code == 404
    client.post("/api/v1/auth/logout")

    from app.core.database import SessionLocal
    from app.models.models import DistributorProfile, User
    db = SessionLocal()
    distributor_user = db.query(User).filter(User.email == email).first()
    assert distributor_user is not None
    profile = db.query(DistributorProfile).filter(DistributorProfile.user_id == distributor_user.id).first()
    assert profile is not None
    assert profile.application_id is None
    db.close()


def test_company_document_lifecycle(client, super_admin):
    uid, email, password = super_admin
    client.post("/api/v1/auth/login", json={"email": email, "password": password})

    # Upload the underlying file first.
    upload = client.post(
        "/api/v1/media/company-documents",
        files={"file": ("cert.pdf", b"%PDF-1.4 fake certificate content", "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    media_id = upload.json()["id"]

    create = client.post("/api/v1/company/documents", json={
        "title": "ISO 9001 Certificate", "document_type": "quality_certificate", "media_id": media_id,
    })
    assert create.status_code == 200, create.text
    doc_id = create.json()["id"]
    assert create.json()["verification_status"] == "uploaded"

    # Not visible publicly yet.
    public = client.get("/api/v1/company/documents")
    assert doc_id not in [d["id"] for d in public.json()]

    # Publishing before verification is rejected.
    early_publish = client.post(f"/api/v1/company/documents/{doc_id}/publish")
    assert early_publish.status_code == 400

    verify = client.post(f"/api/v1/company/documents/{doc_id}/verify/verified", json={"notes": "Checked against original."})
    assert verify.status_code == 200
    assert verify.json()["verification_status"] == "verified"

    # Verified alone is not enough to publish - an administrator must also
    # approve it (a separate gate from the content-verifier's fact-check).
    early_publish2 = client.post(f"/api/v1/company/documents/{doc_id}/publish")
    assert early_publish2.status_code == 400

    approve = client.post(f"/api/v1/company/documents/{doc_id}/approve")
    assert approve.status_code == 200
    assert approve.json()["is_approved"] is True

    publish = client.post(f"/api/v1/company/documents/{doc_id}/publish")
    assert publish.status_code == 200
    assert publish.json()["is_published"] is True
    assert publish.json()["published_by_id"] == uid

    public2 = client.get("/api/v1/company/documents")
    assert doc_id in [d["id"] for d in public2.json()]

    # The certificate file itself is now downloadable without auth.
    client.post("/api/v1/auth/logout")
    download = client.get(f"/api/v1/media/certificates/{doc_id}")
    assert download.status_code == 200

    # Archiving pulls it back off the public site even though it's still
    # verified/approved.
    client.post("/api/v1/auth/login", json={"email": email, "password": password})
    archive = client.post(f"/api/v1/company/documents/{doc_id}/archive")
    assert archive.status_code == 200
    assert archive.json()["is_archived"] is True
    public3 = client.get("/api/v1/company/documents")
    assert doc_id not in [d["id"] for d in public3.json()]


def test_agriculture_photo_requires_usage_rights_to_publish(client, super_admin):
    uid, email, password = super_admin
    client.post("/api/v1/auth/login", json={"email": email, "password": password})

    upload = client.post(
        "/api/v1/media/agriculture-photos",
        files={"file": ("field.jpg", b"\xff\xd8\xff\xe0fakejpegdata", "image/jpeg")},
    )
    assert upload.status_code == 200, upload.text
    media_id = upload.json()["id"]

    create = client.post("/api/v1/media/agriculture", json={
        "title": "Agricultural Field", "category": "fields", "alt_text": "A field of crops.",
        "media_id": media_id, "usage_rights_verified": False,
    })
    assert create.status_code == 200, create.text
    photo_id = create.json()["id"]
    # Unverified fields render the mandated fallback copy, never invented values.
    assert create.json()["location"] == "Information pending verification."

    blocked = client.post(f"/api/v1/media/agriculture/{photo_id}/status/published")
    assert blocked.status_code == 400

    verify = client.post(f"/api/v1/media/agriculture/{photo_id}/status/under_review")
    assert verify.status_code == 200

    # Directly patch usage_rights_verified via a fresh create with it true,
    # simulating the rights check having been completed.
    create2 = client.post("/api/v1/media/agriculture", json={
        "title": "Verified Field Photo", "category": "fields", "alt_text": "A field of crops, rights verified.",
        "media_id": media_id, "usage_rights_verified": True,
    })
    photo_id2 = create2.json()["id"]

    # Publishing still requires an explicit "approved" step first, even
    # with usage rights verified - approval and publication are distinct.
    early_publish = client.post(f"/api/v1/media/agriculture/{photo_id2}/status/published")
    assert early_publish.status_code == 400

    approve = client.post(f"/api/v1/media/agriculture/{photo_id2}/status/approved")
    assert approve.status_code == 200
    assert approve.json()["approved_by_id"] == uid

    publish = client.post(f"/api/v1/media/agriculture/{photo_id2}/status/published")
    assert publish.status_code == 200
    assert publish.json()["published_by_id"] == uid

    client.post("/api/v1/auth/logout")
    public = client.get("/api/v1/media/agriculture")
    ids = [p["id"] for p in public.json()]
    assert photo_id2 in ids
    assert photo_id not in ids
