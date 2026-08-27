import io
import uuid


def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200


def test_announcement_lifecycle_and_visibility(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)
    r = client.post("/api/v1/announcements", json={"title": "Monsoon advisory", "slug": "monsoon-advisory", "body": "Details here."})
    assert r.status_code == 200
    aid = r.json()["id"]
    assert client.get("/api/v1/announcements/public/monsoon-advisory").status_code == 404  # draft not public

    client.post(f"/api/v1/announcements/{aid}/transition/in_review", json={})
    client.post(f"/api/v1/announcements/{aid}/transition/published", json={})
    r = client.get("/api/v1/announcements/public/monsoon-advisory")
    assert r.status_code == 200

    client.post(f"/api/v1/announcements/{aid}/transition/archived", json={})
    assert client.get("/api/v1/announcements/public/monsoon-advisory").status_code == 404


def test_knowledge_article_requires_review_before_publish(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)
    r = client.post("/api/v1/knowledge", json={"title": "Managing aphids", "slug": "managing-aphids", "body": "Content."})
    kid = r.json()["id"]
    assert client.get("/api/v1/knowledge/public/managing-aphids").status_code == 404

    client.post(f"/api/v1/knowledge/{kid}/transition/in_review", json={})
    # cannot jump straight to published without approval
    r = client.post(f"/api/v1/knowledge/{kid}/transition/published", json={})
    assert r.status_code == 400

    client.post(f"/api/v1/knowledge/{kid}/transition/approved", json={})
    r = client.post(f"/api/v1/knowledge/{kid}/transition/published", json={})
    assert r.status_code == 200
    assert client.get("/api/v1/knowledge/public/managing-aphids").status_code == 200


def test_follow_up_task_overdue_flag_and_completion(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)
    r = client.post("/api/v1/tasks", json={"title": "Call dealer", "priority": "high", "due_date": "2020-01-01T00:00:00"})
    tid = r.json()["id"]
    assert r.json()["overdue"] is True

    r = client.post(f"/api/v1/tasks/{tid}/status/completed", json={})
    assert r.status_code == 200
    tasks = client.get("/api/v1/tasks").json()
    completed = next(t for t in tasks if t["id"] == tid)
    assert completed["status"] == "completed"
    assert completed["completed_at"] is not None


def _publish_product(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)
    suffix = uuid.uuid4().hex[:8]
    sku, slug = f"SKU-MEDIA-{suffix}", f"media-product-{suffix}"
    r = client.post("/api/v1/products", json={"sku": sku, "name": "Media Product", "slug": slug,
                                            "precautions": "x", "full_description": "x"})
    pid = r.json()["id"]
    cat = client.post("/api/v1/categories", json={"name": f"Media Cat {suffix}", "slug": f"media-cat-{suffix}"})
    client.put(f"/api/v1/products/{pid}", json={"sku": sku, "name": "Media Product", "slug": slug,
                                              "category_id": cat.json()["id"], "precautions": "x", "full_description": "x"})
    client.post(f"/api/v1/products/{pid}/transition/in_review", json={})
    client.post(f"/api/v1/products/{pid}/transition/approved", json={})
    client.post(f"/api/v1/products/{pid}/transition/published", json={})
    return pid


VALID_PNG = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)


def test_product_image_upload_validated_and_public(client, super_admin):
    pid = _publish_product(client, super_admin)
    files = {"file": ("photo.png", io.BytesIO(VALID_PNG), "image/png")}
    r = client.post(f"/api/v1/media/products/{pid}/images", files=files, params={"alt_text": "Bottle of product"})
    assert r.status_code == 200, r.text
    path = r.json()["file_path"]

    r2 = client.get(f"/api/v1/media/public/{path.split('public/')[-1]}")
    assert r2.status_code == 200


def test_upload_rejects_disguised_file(client, super_admin):
    pid = _publish_product(client, super_admin)
    fake = io.BytesIO(b"<script>alert(1)</script>")
    files = {"file": ("evil.png", fake, "image/png")}
    r = client.post(f"/api/v1/media/products/{pid}/images", files=files, params={"alt_text": "x"})
    assert r.status_code == 400


def test_case_attachment_private_and_access_controlled(client):
    client.post("/api/v1/auth/register", json={"full_name": "Attach Farmer", "email": "attachfarmer@example.com",
                                             "phone": "9876543299", "password": "Passw0rd123"})
    r = client.post("/api/v1/cases", json={"title": "T", "description": "D", "district": "Hyderabad"})
    case_id = r.json()["id"]

    files = {"file": ("photo.png", io.BytesIO(VALID_PNG), "image/png")}
    r = client.post(f"/api/v1/media/cases/{case_id}/attachments", files=files)
    assert r.status_code == 200, r.text
    record_id = r.json()["id"]

    r = client.get(f"/api/v1/media/private/{record_id}")
    assert r.status_code == 200

    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/register", json={"full_name": "Other Farmer", "email": "otherfarmer@example.com",
                                             "phone": "9876543298", "password": "Passw0rd123"})
    r = client.get(f"/api/v1/media/private/{record_id}")
    assert r.status_code == 403
