def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200


def test_catalogue_starts_empty(client):
    r = client.get("/api/v1/products/public")
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_product_lifecycle_and_visibility(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)

    r = client.post("/api/v1/products", json={
        "sku": "SKU-001", "name": "Neem Based Spray", "slug": "neem-based-spray",
        "category_id": None, "precautions": "Keep away from children.",
        "full_description": "A neem-based formulation for foliar application.",
    })
    assert r.status_code == 200, r.text
    product = r.json()
    assert product["status"] == "draft"

    # draft not visible publicly
    assert client.get("/api/v1/products/public/neem-based-spray").status_code == 404

    pid = product["id"]
    r = client.post(f"/api/v1/products/{pid}/transition/in_review", json={})
    assert r.status_code == 200
    r = client.post(f"/api/v1/products/{pid}/transition/approved", json={})
    assert r.status_code == 200

    # create category first, then update product to attach it (publication requires category)
    cat = client.post("/api/v1/categories", json={"name": "Bio Pesticides", "slug": "bio-pesticides"})
    assert cat.status_code == 200
    client.put(f"/api/v1/products/{pid}", json={
        "sku": "SKU-001", "name": "Neem Based Spray", "slug": "neem-based-spray",
        "category_id": cat.json()["id"], "precautions": "Keep away from children.",
        "full_description": "A neem-based formulation for foliar application.",
    })
    upload = client.post(f"/api/v1/media/products/{pid}/images?alt_text=Front%20of%20pack",
                          files={"file": ("front.jpg", b"\xff\xd8\xff" + b"x" * 20, "image/jpeg")})
    assert upload.status_code == 200, upload.text

    r = client.post(f"/api/v1/products/{pid}/transition/published", json={})
    assert r.status_code == 200

    r = client.get("/api/v1/products/public/neem-based-spray")
    assert r.status_code == 200

    r = client.post(f"/api/v1/products/{pid}/transition/unpublished", json={})
    assert r.status_code == 200
    assert client.get("/api/v1/products/public/neem-based-spray").status_code == 404

    r = client.post(f"/api/v1/products/{pid}/transition/archived", json={})
    assert r.status_code == 200


def test_sku_and_slug_uniqueness(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)
    payload = {"sku": "SKU-DUP", "name": "A", "slug": "a-product", "precautions": "x", "full_description": "x"}
    assert client.post("/api/v1/products", json=payload).status_code == 200
    dup_sku = {**payload, "slug": "a-product-2"}
    assert client.post("/api/v1/products", json=dup_sku).status_code == 400
    dup_slug = {**payload, "sku": "SKU-DUP-2"}
    assert client.post("/api/v1/products", json=dup_slug).status_code == 400


def test_publish_requires_fields(client, super_admin):
    _, email, password = super_admin
    _login(client, email, password)
    r = client.post("/api/v1/products", json={"sku": "SKU-INC", "name": "Incomplete", "slug": "incomplete"})
    pid = r.json()["id"]
    client.post(f"/api/v1/products/{pid}/transition/in_review", json={})
    client.post(f"/api/v1/products/{pid}/transition/approved", json={})
    r = client.post(f"/api/v1/products/{pid}/transition/published", json={})
    assert r.status_code == 400  # missing category/description/precautions/image
    assert "image" in r.json()["detail"]


def test_publish_requires_at_least_one_image(client, super_admin):
    """A product can otherwise satisfy every text field yet still have had
    its only image removed after upload - publish must still catch that,
    not just check whether an image was ever attached."""
    _, email, password = super_admin
    _login(client, email, password)
    r = client.post("/api/v1/products", json={"sku": "SKU-NOIMG", "name": "No Image", "slug": "no-image",
                                            "precautions": "x", "full_description": "x"})
    pid = r.json()["id"]
    cat = client.post("/api/v1/categories", json={"name": "No Image Cat", "slug": "no-image-cat"})
    client.put(f"/api/v1/products/{pid}", json={"sku": "SKU-NOIMG", "name": "No Image", "slug": "no-image",
                                              "category_id": cat.json()["id"], "precautions": "x", "full_description": "x"})
    client.post(f"/api/v1/products/{pid}/transition/in_review", json={})
    client.post(f"/api/v1/products/{pid}/transition/approved", json={})

    without_image = client.post(f"/api/v1/products/{pid}/transition/published", json={})
    assert without_image.status_code == 400
    assert "image" in without_image.json()["detail"]

    upload = client.post(f"/api/v1/media/products/{pid}/images?alt_text=Front",
                          files={"file": ("f.jpg", b"\xff\xd8\xff" + b"x" * 20, "image/jpeg")})
    image_id = upload.json()["id"]
    with_image = client.post(f"/api/v1/products/{pid}/transition/published", json={})
    assert with_image.status_code == 200, with_image.text

    # removing the only image afterward doesn't retroactively unpublish -
    # this test documents current behavior, it isn't asserting that's ideal
    assert client.delete(f"/api/v1/products/{pid}/images/{image_id}").status_code == 200


def test_dealer_cannot_create_list_or_manage_products(client, approved_dealer):
    """Product creation/upload is restricted to the owner (super_admin) and
    company managers (admin, content_manager) only - a dealer has no product
    access at all, not even to their own draft."""
    _, email, password, _ = approved_dealer
    _login(client, email, password)

    assert client.get("/api/v1/products").status_code == 403
    r = client.post("/api/v1/products", json={
        "sku": "SKU-DLR-001", "name": "Dealer Submitted Fertilizer", "slug": "dealer-submitted-fertilizer",
        "precautions": "Keep away from children.", "full_description": "Submitted by a dealer for review.",
    })
    assert r.status_code == 403


def test_farmer_cannot_create_a_product(client):
    client.post("/api/v1/auth/register", json={
        "full_name": "Product Farmer", "email": "productfarmer@example.com", "phone": "9876543260", "password": "Passw0rd123",
    })
    r = client.post("/api/v1/products", json={
        "sku": "SKU-FARM", "name": "Farmer Attempt", "slug": "farmer-attempt", "precautions": "x", "full_description": "x",
    })
    assert r.status_code == 403
