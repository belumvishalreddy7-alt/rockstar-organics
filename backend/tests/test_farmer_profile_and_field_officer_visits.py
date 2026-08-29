"""Tests for the 2026-08-29 additions: a farmer's self-service profile
endpoint (previously the farm data collected at registration had no way
for the farmer to view/edit it) and a field officer's own assigned-visits
view (previously only a staff-wide, admin-facing visit list existed)."""
import datetime as dt


def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200


def _make_farmer(client, email="farmerprofile@example.com"):
    client.post("/api/v1/auth/register", json={
        "full_name": "Profile Farmer", "email": email, "phone": "9876543260", "password": "Passw0rd123",
    })


def test_farmer_can_view_and_update_own_profile(client):
    _make_farmer(client)
    r = client.get("/api/v1/farmers/me/profile")
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "Telangana"  # the registration-time default
    assert r.json()["district"] is None

    update = client.put("/api/v1/farmers/me/profile", json={
        "district": "Rangareddy", "mandal": "Serilingampally", "village": "Gopanpally",
        "pin_code": "500046", "farm_size": 2.5, "farm_size_unit": "acres",
        "main_crops": "Paddy, Cotton", "irrigation_type": "borewell", "preferred_language": "te",
    })
    assert update.status_code == 200, update.text
    assert update.json()["district"] == "Rangareddy"
    assert update.json()["irrigation_type"] == "borewell"

    reread = client.get("/api/v1/farmers/me/profile")
    assert reread.json()["village"] == "Gopanpally"
    assert reread.json()["preferred_language"] == "te"


def test_farmer_profile_rejects_invalid_values(client):
    _make_farmer(client, "farmerprofile2@example.com")
    bad_pin = client.put("/api/v1/farmers/me/profile", json={"pin_code": "12"})
    assert bad_pin.status_code == 422
    bad_irrigation = client.put("/api/v1/farmers/me/profile", json={"irrigation_type": "not-a-real-type"})
    assert bad_irrigation.status_code == 422


def test_non_farmer_cannot_access_farmer_profile_endpoint(client, sales_manager):
    _, email, password = sales_manager
    _login(client, email, password)
    r = client.get("/api/v1/farmers/me/profile")
    assert r.status_code == 403


def test_field_officer_sees_only_their_own_assigned_visits(client, super_admin, field_officer):
    _, admin_email, admin_password = super_admin
    _, officer_email, officer_password = field_officer

    _make_farmer(client, "farmervisit@example.com")
    case = client.post("/api/v1/cases", json={
        "title": "Wilting plants", "description": "desc", "district": "Hyderabad", "mandal": "Serilingampally",
    })
    case_id = case.json()["id"]
    visit = client.post("/api/v1/visits", json={"case_id": case_id, "purpose": "Field inspection"})
    assert visit.status_code == 200, visit.text
    visit_id = visit.json()["id"]
    client.post("/api/v1/auth/logout")

    _login(client, admin_email, admin_password)
    start = dt.datetime.utcnow() + dt.timedelta(days=1)
    end = start + dt.timedelta(hours=1)
    schedule = client.post(f"/api/v1/visits/{visit_id}/schedule", json={
        "assigned_officer_id": field_officer[0], "scheduled_start": start.isoformat(), "scheduled_end": end.isoformat(),
    })
    assert schedule.status_code == 200, schedule.text
    client.post("/api/v1/auth/logout")

    _login(client, officer_email, officer_password)
    mine = client.get("/api/v1/visits/assigned-to-me")
    assert mine.status_code == 200
    assert len(mine.json()) == 1
    assert mine.json()[0]["case_reference"] is not None
    assert mine.json()[0]["farmer_name"] == "Profile Farmer"


def test_farmer_cannot_access_field_officer_visit_list(client):
    _make_farmer(client, "farmervisit2@example.com")
    r = client.get("/api/v1/visits/assigned-to-me")
    assert r.status_code == 403
