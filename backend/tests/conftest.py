"""Pytest fixtures: a fresh SQLite temp database per test session, plus
helper factories for staff/dealer/farmer accounts."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db.name}"
os.environ["ENVIRONMENT"] = "test"
os.environ["DEV_EXPOSE_RESET_TOKEN"] = "true"
os.environ["UPLOAD_ROOT"] = tempfile.mkdtemp(prefix="rso-uploads-")

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.core.permissions import ROLE_ADMIN, ROLE_DEALER, ROLE_FARMER, ROLE_FIELD_OFFICER, ROLE_SALES_MANAGER, ROLE_SUPER_ADMIN
from app.core.security import hash_password
from app.main import app
from app.models.models import DealerProfile, DealerServiceArea, User


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The rate limiter is a process-wide singleton keyed partly by client
    IP, and every TestClient request reports the same synthetic IP - so
    without a reset, unrelated tests would trip each other's rate limits
    (registration, login, enquiry, review, etc. all share the counter
    across the whole test session otherwise). Production has real, distinct
    client IPs, so this is purely a test-isolation concern."""
    from app.core.rate_limit import rate_limiter
    rate_limiter._hits.clear()
    yield
    rate_limiter._hits.clear()


class CsrfSyncClient(TestClient):
    """A TestClient that automatically echoes the `rso_csrf` cookie into the
    `X-CSRF-Token` header on every request, mirroring what the real
    frontend does (see src/api/client.ts). Without this, every test that
    logs in and then performs a POST/PUT/DELETE would need to manually
    thread the CSRF token through - this keeps test code focused on
    behavior rather than plumbing."""

    def request(self, method, url, *args, **kwargs):
        csrf_token = self.cookies.get("rso_csrf")
        if csrf_token:
            headers = kwargs.get("headers") or {}
            headers = {**headers, "x-csrf-token": csrf_token}
            kwargs["headers"] = headers
        return super().request(method, url, *args, **kwargs)


@pytest.fixture()
def client():
    return CsrfSyncClient(app)


def _make_user(role: str, email: str, password: str = "Passw0rd123", status: str = "active"):
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        user = User(email=email, password_hash=hash_password(password), role=role, full_name=email.split("@")[0], status=status)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id, email, password
    finally:
        db.close()


@pytest.fixture()
def super_admin():
    return _make_user(ROLE_SUPER_ADMIN, f"superadmin-{uuid.uuid4().hex[:8]}@example.com")


@pytest.fixture()
def sales_manager():
    return _make_user(ROLE_SALES_MANAGER, f"sales-{uuid.uuid4().hex[:8]}@example.com")


@pytest.fixture()
def field_officer():
    return _make_user(ROLE_FIELD_OFFICER, f"officer-{uuid.uuid4().hex[:8]}@example.com")


@pytest.fixture()
def logged_in_client(client):
    def _login_as(email, password):
        r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        return client
    return _login_as


@pytest.fixture()
def approved_dealer():
    """Creates a dealer user + profile directly (bypassing the application
    flow) for tests that only need an already-approved dealer."""
    from app.core.database import SessionLocal
    uid, email, password = _make_user(ROLE_DEALER, f"dealer-{uuid.uuid4().hex[:8]}@example.com")
    db = SessionLocal()
    try:
        profile = DealerProfile(user_id=uid, business_name="Test Agro Traders", district="Hyderabad",
                                 directory_opt_in=True, farmer_case_opt_in=True)
        db.add(profile)
        db.flush()
        db.add(DealerServiceArea(dealer_id=profile.id, district="Hyderabad", mandal="Serilingampally"))
        db.commit()
        db.refresh(profile)
        return uid, email, password, profile.id
    finally:
        db.close()
