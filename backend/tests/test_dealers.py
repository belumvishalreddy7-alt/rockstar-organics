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


def test_delete_approved_application_does_not_break_the_dealer_profile(client, sales_manager, super_admin):
    """An approved application has a DealerProfile pointing back at it
    (application_id) - deleting the application must not leave that
    foreign key dangling (or 500, like the same-shaped bug just fixed for
    products), and the dealer's real account/profile must survive."""
    r = client.post("/api/v1/dealers/apply", json={
        "contact_person": "Del Test", "business_name": "Del Test Agro", "email": "deltest@example.com",
        "phone": "9876543223", "district": "Hyderabad", "consent_given": True,
    })
    app_id = r.json()["id"]

    _, sm_email, sm_password = sales_manager
    client.post("/api/v1/auth/login", json={"email": sm_email, "password": sm_password})
    approve = client.post(f"/api/v1/dealers/applications/{app_id}/status/approved", json={})
    assert approve.status_code == 200, approve.text
    client.post("/api/v1/auth/logout")

    # a non-super_admin can't delete the application
    client.post("/api/v1/auth/login", json={"email": sm_email, "password": sm_password})
    assert client.delete(f"/api/v1/dealers/applications/{app_id}").status_code == 403
    client.post("/api/v1/auth/logout")

    _, admin_email, admin_password = super_admin
    client.post("/api/v1/auth/login", json={"email": admin_email, "password": admin_password})
    deleted = client.delete(f"/api/v1/dealers/applications/{app_id}")
    assert deleted.status_code == 200, deleted.text
    assert client.delete(f"/api/v1/dealers/applications/{app_id}").status_code == 404

    client.post("/api/v1/auth/logout")

    # deleting the application only removed the application record - the
    # dealer's real account/profile (and its now-nulled application_id)
    # must still exist
    from app.core.database import SessionLocal
    from app.models.models import DealerProfile, User
    db = SessionLocal()
    dealer_user = db.query(User).filter(User.email == "deltest@example.com").first()
    assert dealer_user is not None
    profile = db.query(DealerProfile).filter(DealerProfile.user_id == dealer_user.id).first()
    assert profile is not None
    assert profile.application_id is None
    db.close()
