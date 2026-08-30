"""Tests for public employment (staff) applications - the only path a
staff account can come to exist through besides an existing owner/admin
directly using staff.invite. Covers: anyone can submit an application;
only owner/admin can review/approve; approving creates a real account with
the admin-chosen role (not necessarily what the applicant requested); only
a super_admin can grant super_admin; submitting never grants access by
itself."""
import uuid


def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text


def _submit(client, email="applicant@example.com", position="field_officer"):
    r = client.post("/api/v1/staff-applications", json={
        "full_name": "Test Applicant", "email": email, "phone": "9876543212",
        "position_applied_for": position, "notes": "Interested in field work.", "consent_given": True,
    })
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_anonymous_can_submit_but_gets_no_access(client):
    aid = _submit(client, email=f"anon-{uuid.uuid4().hex[:8]}@example.com")
    assert client.get("/api/v1/staff-applications").status_code == 401
    # no account exists for this email until an admin approves
    login_attempt = client.post("/api/v1/auth/login", json={"email": "anon@example.com", "password": "whatever"})
    assert login_attempt.status_code == 401


def test_only_content_manager_position_allowed_and_admin_or_below_rejected_from_reviewing(client, sales_manager):
    bad = client.post("/api/v1/staff-applications", json={
        "full_name": "Bad Position", "email": "bad@example.com", "phone": "9876543213",
        "position_applied_for": "super_admin", "consent_given": True,
    })
    assert bad.status_code == 422

    aid = _submit(client, email=f"gate-{uuid.uuid4().hex[:8]}@example.com")
    _, email, password = sales_manager
    _login(client, email, password)
    # sales_manager is staff but not SETTINGS_MANAGERS (owner/admin only)
    assert client.get("/api/v1/staff-applications").status_code == 403
    assert client.post(f"/api/v1/staff-applications/{aid}/approve", json={"role": "field_officer"}).status_code == 403


def test_admin_can_approve_with_a_different_role_than_requested(client, super_admin):
    email = f"approve-{uuid.uuid4().hex[:8]}@example.com"
    aid = _submit(client, email=email, position="field_officer")

    _, admin_email, admin_password = super_admin
    _login(client, admin_email, admin_password)

    listed = client.get("/api/v1/staff-applications").json()
    assert any(a["id"] == aid and a["position_applied_for"] == "field_officer" for a in listed)

    # the admin grants a different role than what was requested
    approve = client.post(f"/api/v1/staff-applications/{aid}/approve", json={"role": "content_manager"})
    assert approve.status_code == 200, approve.text
    creds = approve.json()["staff_credentials"]
    assert creds["email"] == email

    client.post("/api/v1/auth/logout")
    new_login = client.post("/api/v1/auth/login", json={"email": email, "password": creds["temporary_password"]})
    assert new_login.status_code == 200
    assert new_login.json()["role"] == "content_manager"
    assert new_login.json()["must_change_password"] is True

    # already-approved applications can't be approved again
    client.post("/api/v1/auth/logout")
    _login(client, admin_email, admin_password)
    assert client.post(f"/api/v1/staff-applications/{aid}/approve", json={"role": "field_officer"}).status_code == 400


def test_admin_cannot_grant_super_admin_only_super_admin_can(client, super_admin):
    from app.core.permissions import ROLE_ADMIN
    from tests.conftest import _make_user

    admin_email, admin_password = f"admin-{uuid.uuid4().hex[:8]}@example.com", "Passw0rd123"
    _make_user(ROLE_ADMIN, admin_email, admin_password)
    aid = _submit(client, email=f"superwannabe-{uuid.uuid4().hex[:8]}@example.com")

    _login(client, admin_email, admin_password)
    denied = client.post(f"/api/v1/staff-applications/{aid}/approve", json={"role": "super_admin"})
    assert denied.status_code == 403
    client.post("/api/v1/auth/logout")

    _, super_email, super_password = super_admin
    _login(client, super_email, super_password)
    allowed = client.post(f"/api/v1/staff-applications/{aid}/approve", json={"role": "super_admin"})
    assert allowed.status_code == 200, allowed.text


def test_reject_and_duplicate_email_detection(client, super_admin):
    email = f"reject-{uuid.uuid4().hex[:8]}@example.com"
    aid = _submit(client, email=email)
    second_aid = _submit(client, email=email)  # duplicate open application

    _, admin_email, admin_password = super_admin
    _login(client, admin_email, admin_password)

    reject = client.post(f"/api/v1/staff-applications/{aid}/status/rejected", json={"reason": "Not a fit."})
    assert reject.status_code == 200
    assert reject.json()["status"] == "rejected"

    # rejected application cannot be approved afterward
    assert client.post(f"/api/v1/staff-applications/{aid}/approve", json={"role": "field_officer"}).status_code == 400

    # the duplicate can still be approved independently
    approve_second = client.post(f"/api/v1/staff-applications/{second_aid}/approve", json={"role": "field_officer"})
    assert approve_second.status_code == 200, approve_second.text

    # a third application for the now-real account's email is blocked at approval time
    third_aid = _submit(client, email=email)
    blocked = client.post(f"/api/v1/staff-applications/{third_aid}/approve", json={"role": "field_officer"})
    assert blocked.status_code == 400
