def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200


def _make_farmer(client, email="farmer_case@example.com"):
    client.post("/api/v1/auth/register", json={
        "full_name": "Case Farmer", "email": email, "phone": "9876543230", "password": "Passw0rd123",
    })


def test_farmer_case_submission_and_isolation(client):
    _make_farmer(client, "farmerA@example.com")
    r = client.post("/api/v1/cases", json={
        "title": "Yellowing leaves", "description": "Leaves turning yellow after rain.",
        "district": "Hyderabad", "mandal": "Serilingampally", "crop": "Paddy",
    })
    assert r.status_code == 200
    case_id = r.json()["id"]

    client.post("/api/v1/auth/logout")
    _make_farmer(client, "farmerB@example.com")
    r = client.get(f"/api/v1/cases/{case_id}")
    assert r.status_code == 403  # farmer B cannot see farmer A's case


def test_matching_by_district_and_mandal(client, approved_dealer, sales_manager):
    _, dealer_email, dealer_password, dealer_id = approved_dealer
    _make_farmer(client, "farmerC@example.com")
    r = client.post("/api/v1/cases", json={
        "title": "Pest issue", "description": "Pests on cotton crop.",
        "district": "Hyderabad", "mandal": "Serilingampally", "crop": "Cotton",
    })
    case_id = r.json()["id"]
    client.post("/api/v1/auth/logout")

    _, email, password = sales_manager
    _login(client, email, password)
    matches = client.get(f"/api/v1/cases/{case_id}/matches").json()
    assert any(m["dealer_id"] == dealer_id and m["mandal_match"] for m in matches)

    r = client.post(f"/api/v1/cases/{case_id}/assign", json={"dealer_id": dealer_id})
    assert r.status_code == 200

    r = client.get(f"/api/v1/cases/{case_id}")
    assert r.json()["assigned_dealer_id"] == dealer_id


def test_dealer_opt_out_excluded_from_matches(client, approved_dealer, sales_manager):
    from app.core.database import SessionLocal
    from app.models.models import DealerProfile

    _, _, _, dealer_id = approved_dealer
    db = SessionLocal()
    d = db.get(DealerProfile, dealer_id)
    d.farmer_case_opt_in = False
    db.commit()
    db.close()

    _make_farmer(client, "farmerD@example.com")
    r = client.post("/api/v1/cases", json={
        "title": "Issue", "description": "desc", "district": "Hyderabad", "mandal": "Serilingampally",
    })
    case_id = r.json()["id"]
    client.post("/api/v1/auth/logout")

    _, email, password = sales_manager
    _login(client, email, password)
    matches = client.get(f"/api/v1/cases/{case_id}/matches").json()
    assert not any(m["dealer_id"] == dealer_id for m in matches)


def test_private_notes_hidden_from_farmer(client, sales_manager):
    _make_farmer(client, "farmerE@example.com")
    r = client.post("/api/v1/cases", json={"title": "T", "description": "D", "district": "Hyderabad"})
    case_id = r.json()["id"]
    client.post("/api/v1/auth/logout")

    _, email, password = sales_manager
    _login(client, email, password)
    client.post(f"/api/v1/cases/{case_id}/messages", json={"body": "Internal note: check dosage history", "is_private": True})
    client.post("/api/v1/auth/logout")

    client.post("/api/v1/auth/login", json={"email": "farmerE@example.com", "password": "Passw0rd123"})
    r = client.get(f"/api/v1/cases/{case_id}")
    bodies = [m["body"] for m in r.json()["timeline"]]
    assert "Internal note: check dosage history" not in bodies
