"""Tests for the 2026-08-28 single-active-session enforcement and the
owner (super_admin) in-app notification on farmer/dealer/distributor
logins."""
import app.main as main_module
from starlette.testclient import TestClient as PlainTestClient


def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r


def test_second_login_invalidates_the_first_session(client):
    client.post("/api/v1/auth/register", json={
        "full_name": "Session Farmer Two", "email": "sessionfarmer2@example.com", "phone": "9876543250", "password": "Passw0rd123",
    })
    first_session_cookies = dict(client.cookies)

    # Log in again with the same credentials from a second, independent
    # client (simulating a second device/browser) - a fresh registration
    # already established a session, so log in again explicitly to trigger
    # the rotation on a distinct request.
    second = PlainTestClient(main_module.app)
    r = second.post("/api/v1/auth/login", json={"email": "sessionfarmer2@example.com", "password": "Passw0rd123"})
    assert r.status_code == 200
    otp_body = r.json()
    assert otp_body["otp_required"] is True  # farmer logins require the emailed code too now
    r = second.post("/api/v1/auth/login/verify-otp", json={"email": "sessionfarmer2@example.com", "code": otp_body["dev_otp_code"]})
    assert r.status_code == 200

    # The original (first) session must now be rejected.
    first = PlainTestClient(main_module.app)
    first.cookies.update(first_session_cookies)
    r = first.get("/api/v1/auth/me")
    assert r.json() is None

    # The second (newest) session still works.
    r = second.get("/api/v1/auth/me")
    assert r.json() is not None
    assert r.json()["email"] == "sessionfarmer2@example.com"


def test_farmer_login_notifies_super_admin(client, super_admin):
    _, admin_email, admin_password = super_admin

    client.post("/api/v1/auth/register", json={
        "full_name": "Notify Farmer", "email": "notifyfarmer@example.com", "phone": "9876543251", "password": "Passw0rd123",
    })
    client.post("/api/v1/auth/logout")
    _login(client, "notifyfarmer@example.com", "Passw0rd123")
    client.post("/api/v1/auth/logout")

    _login(client, admin_email, admin_password)
    notifications = client.get("/api/v1/notifications").json()
    assert any(n["type"] == "user_login" and "Notify Farmer" in n["message"] for n in notifications)


def test_staff_login_does_not_notify_owner(client, super_admin, sales_manager):
    _, admin_email, admin_password = super_admin
    _, sm_email, sm_password = sales_manager

    _login(client, sm_email, sm_password)
    client.post("/api/v1/auth/logout")

    _login(client, admin_email, admin_password)
    notifications = client.get("/api/v1/notifications").json()
    assert not any(n["type"] == "user_login" and sm_email in n["message"] for n in notifications)


def test_dealer_login_notifies_super_admin(client, super_admin, approved_dealer):
    _, admin_email, admin_password = super_admin
    _, dealer_email, dealer_password, _ = approved_dealer

    _login(client, dealer_email, dealer_password)
    client.post("/api/v1/auth/logout")

    _login(client, admin_email, admin_password)
    notifications = client.get("/api/v1/notifications").json()
    assert any(n["type"] == "user_login" and dealer_email in n["message"] for n in notifications)
