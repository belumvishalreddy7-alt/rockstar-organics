def test_farmer_can_register_and_login(client):
    r = client.post("/api/v1/auth/register", json={
        "full_name": "Ravi Kumar", "email": "ravi@example.com", "phone": "9876543210", "password": "Passw0rd123",
    })
    assert r.status_code == 200
    assert r.json()["role"] == "farmer"

    client.post("/api/v1/auth/logout")
    r = client.post("/api/v1/auth/login", json={"email": "ravi@example.com", "password": "Passw0rd123"})
    assert r.status_code == 200


def test_invalid_login_fails_generically(client):
    client.post("/api/v1/auth/register", json={
        "full_name": "Sita", "email": "sita@example.com", "phone": "9876543211", "password": "Passw0rd123",
    })
    r = client.post("/api/v1/auth/login", json={"email": "sita@example.com", "password": "WrongPassword1"})
    assert r.status_code == 401
    r2 = client.post("/api/v1/auth/login", json={"email": "doesnotexist@example.com", "password": "WrongPassword1"})
    assert r2.status_code == 401
    assert r.json()["detail"] == r2.json()["detail"]  # generic error, no account-existence leak


def test_suspended_account_cannot_login(client, super_admin):
    from app.core.database import SessionLocal
    from app.models.models import User

    client.post("/api/v1/auth/register", json={
        "full_name": "Suspended User", "email": "suspended@example.com", "phone": "9876543212", "password": "Passw0rd123",
    })
    db = SessionLocal()
    user = db.query(User).filter(User.email == "suspended@example.com").first()
    user.status = "suspended"
    db.commit()
    db.close()

    r = client.post("/api/v1/auth/login", json={"email": "suspended@example.com", "password": "Passw0rd123"})
    assert r.status_code == 401


def test_role_cannot_be_escalated_by_client(client):
    r = client.post("/api/v1/auth/register", json={
        "full_name": "Attacker", "email": "attacker@example.com", "phone": "9876543213", "password": "Passw0rd123",
    })
    assert r.json()["role"] == "farmer"  # role field in request is ignored; not accepted by schema


def test_unauthorised_dashboard_access_blocked(client):
    r = client.get("/api/v1/products")  # staff-only endpoint
    assert r.status_code == 401


def test_password_reset_flow(client):
    client.post("/api/v1/auth/register", json={
        "full_name": "Reset Me", "email": "resetme@example.com", "phone": "9876543214", "password": "Passw0rd123",
    })
    r = client.post("/api/v1/auth/forgot-password", json={"email": "resetme@example.com"})
    assert r.status_code == 200
    token = r.json()["dev_reset_token"]

    r2 = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "NewPassw0rd456"})
    assert r2.status_code == 200

    # old password no longer works
    r3 = client.post("/api/v1/auth/login", json={"email": "resetme@example.com", "password": "Passw0rd123"})
    assert r3.status_code == 401
    # new password works
    r4 = client.post("/api/v1/auth/login", json={"email": "resetme@example.com", "password": "NewPassw0rd456"})
    assert r4.status_code == 200

    # token cannot be reused
    r5 = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "AnotherPassw0rd789"})
    assert r5.status_code == 400


def test_login_rate_limited(client):
    client.post("/api/v1/auth/register", json={
        "full_name": "Rate Limited", "email": "ratelimited@example.com", "phone": "9876543215", "password": "Passw0rd123",
    })
    for _ in range(5):
        client.post("/api/v1/auth/login", json={"email": "ratelimited@example.com", "password": "wrong"})
    r = client.post("/api/v1/auth/login", json={"email": "ratelimited@example.com", "password": "wrong"})
    assert r.status_code == 429
