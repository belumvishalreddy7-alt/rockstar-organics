def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200


def test_dealer_application_and_approval_creates_user(client, sales_manager):
    r = client.post("/api/v1/dealers/apply", json={
        "contact_person": "Anil Reddy", "business_name": "Anil Agro Store", "email": "anilagro@example.com",
        "phone": "9876543220", "district": "Ranga Reddy", "consent_given": True,
    })
    assert r.status_code == 200
    ref = r.json()["reference_number"]

    _, email, password = sales_manager
    _login(client, email, password)
    apps = client.get("/api/v1/dealers/applications").json()
    app_id = next(a["id"] for a in apps if a["reference_number"] == ref)

    r = client.post(f"/api/v1/dealers/applications/{app_id}/status/approved", json={})
    assert r.status_code == 200, r.text
    creds = r.json()["dealer_credentials"]
    assert creds["email"] == "anilagro@example.com"

    # approval alone (no separate opt-in step) makes the dealer findable by
    # farmers in the public directory
    directory = client.get("/api/v1/dealers/directory", params={"district": "Ranga Reddy"}).json()
    assert any(d["business_name"] == "Anil Agro Store" and d["public_phone"] == "9876543220" for d in directory)

    # new dealer can log in with temp password and must change it
    client.post("/api/v1/auth/logout")
    r = client.post("/api/v1/auth/login", json={"email": creds["email"], "password": creds["temporary_password"]})
    assert r.status_code == 200
    assert r.json()["must_change_password"] is True


def test_duplicate_application_flagged(client):
    payload = {"contact_person": "A", "business_name": "B", "email": "dup@example.com", "phone": "9876543221",
               "district": "Hyderabad", "consent_given": True}
    r1 = client.post("/api/v1/dealers/apply", json=payload)
    r2 = client.post("/api/v1/dealers/apply", json=payload)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r2.json()["duplicate_warning"] is True


def test_consent_required(client):
    r = client.post("/api/v1/dealers/apply", json={
        "contact_person": "A", "business_name": "B", "email": "noconsent@example.com", "phone": "9876543222",
        "district": "Hyderabad", "consent_given": False,
    })
    assert r.status_code == 422


def test_directory_respects_opt_in_and_suspension(client, approved_dealer):
    uid, email, password, dealer_id = approved_dealer
    r = client.get("/api/v1/dealers/directory", params={"district": "Hyderabad"})
    assert any(d["id"] == dealer_id for d in r.json())

    from app.core.database import SessionLocal
    from app.models.models import DealerProfile
    db = SessionLocal()
    d = db.get(DealerProfile, dealer_id)
    d.directory_opt_in = False
    db.commit()
    db.close()

    r = client.get("/api/v1/dealers/directory", params={"district": "Hyderabad"})
    assert not any(d["id"] == dealer_id for d in r.json())
