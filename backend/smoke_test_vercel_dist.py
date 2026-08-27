"""
End-to-end smoke test of the CONSOLIDATED deploy artifact (vercel_dist/),
run with production-like settings (same values going into the real .env,
except DATABASE_URL which is a throwaway local SQLite file - the pooler
isn't reachable from this sandbox at all, so DB *connectivity* is verified
separately, after deployment, against the live URL).

Exercises: health, ready, superadmin bootstrap + login, public product
listing, and the full signup -> OTP -> verify -> session flow.
"""
import sys

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
failures = []


def check(label, cond, detail=""):
    status = "OK" if cond else "FAIL"
    print(f"[{status}] {label} {detail}")
    if not cond:
        failures.append(label)


r = client.get("/api/health")
check("GET /api/health", r.status_code == 200, r.text)

r = client.get("/api/ready")
check("GET /api/ready", r.status_code == 200, r.text)
check("ready reports database connected", r.json().get("database") == "connected", r.text)

r = client.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": "Str0ngPassw0rd!"})
check("superadmin login", r.status_code == 200 and r.json()["role"] == "super_admin", f"status={r.status_code} body={r.text}")
csrf_cookie = client.cookies.get("rso_csrf")
check("csrf cookie set on login", bool(csrf_cookie))

r = client.get("/api/v1/products/public")
check("GET /api/v1/products/public", r.status_code == 200 and "items" in r.json(), r.text)

r = client.get("/api/v1/settings/public")
check("GET /api/v1/settings/public", r.status_code == 200, r.text)

# Full real signup -> OTP -> verify flow (dev_otp_code is how we read the
# code back out in this sandbox test; the live deployment additionally
# genuinely attempts real delivery via Brevo on the same call).
signup_email = "smoketest.farmer@example.com"
r = client.post("/api/v1/auth/signup", json={
    "full_name": "Smoke Test Farmer", "email": signup_email, "phone": "9876543210", "password": "Str0ngPassw0rd!",
})
check("POST /api/v1/auth/signup", r.status_code == 200, f"status={r.status_code} body={r.text}")
otp = r.json().get("dev_otp_code")
check("signup response exposes dev_otp_code", bool(otp), r.text)

r = client.post("/api/v1/auth/verify-otp", json={"email": signup_email, "code": otp or "000000"})
check("POST /api/v1/auth/verify-otp", r.status_code == 200 and r.json()["email"] == signup_email, f"status={r.status_code} body={r.text}")

r = client.post("/api/v1/auth/login", json={"email": signup_email, "password": "Str0ngPassw0rd!"})
check("login as newly-verified farmer", r.status_code == 200, f"status={r.status_code} body={r.text}")

r = client.post("/api/v1/auth/forgot-password", json={"email": signup_email})
check("POST /api/v1/auth/forgot-password", r.status_code == 200, r.text)
reset_token = r.json().get("dev_reset_token")
check("forgot-password response exposes dev_reset_token", bool(reset_token), r.text)

r = client.post("/api/v1/auth/reset-password", json={"token": reset_token or "x", "new_password": "AnotherStr0ngPass!"})
check("POST /api/v1/auth/reset-password", r.status_code == 200, f"status={r.status_code} body={r.text}")

r = client.post("/api/v1/auth/login", json={"email": signup_email, "password": "AnotherStr0ngPass!"})
check("login with newly reset password", r.status_code == 200, f"status={r.status_code} body={r.text}")

print()
if failures:
    print(f"{len(failures)} FAILURE(S):", failures)
    sys.exit(1)
print("ALL CHECKS PASSED")
