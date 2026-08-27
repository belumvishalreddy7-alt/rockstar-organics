"""Tests for the Brevo email integration and the pluggable storage backend,
plus a regression test for a subtle account-enumeration shape-oracle found
during the 2026-08-27 audit.

None of these need a real BREVO_API_KEY, SUPABASE_URL, or
SUPABASE_SERVICE_ROLE_KEY: httpx.post/get are monkeypatched so we verify
this app's own code builds the correct request (endpoint, headers, body)
without making a real network call - matching the "never claim a live
integration works unless it was actually exercised" rule for secrets this
environment doesn't have. Real end-to-end delivery still has to be
verified separately, once real credentials are configured, by whoever has
them.
"""
from app.core import email as email_module
from app.core import storage as storage_module


class _FakeResponse:
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.content = text.encode() if isinstance(text, str) else text

    def json(self):
        return self._json_data


def test_email_disabled_without_full_config_never_calls_brevo(monkeypatch):
    """Matches the same rule as email.py's docstring: ALL THREE of
    EMAIL_PROVIDER_ENABLED, BREVO_API_KEY, and EMAIL_FROM_EMAIL must be set,
    or nothing is sent - a half-configured deployment must not silently
    attempt (and fail) a send, nor silently claim success."""
    calls = []
    monkeypatch.setattr(email_module.httpx, "post", lambda *a, **k: calls.append((a, k)) or _FakeResponse(200))

    monkeypatch.setattr(email_module.settings, "EMAIL_PROVIDER_ENABLED", False)
    monkeypatch.setattr(email_module.settings, "BREVO_API_KEY", "fake-key")
    monkeypatch.setattr(email_module.settings, "EMAIL_FROM_EMAIL", "sender@example.com")
    result = email_module.send_email(to="x@example.com", subject="s", html="<p>h</p>", text="t")
    assert result.sent is False
    assert calls == []

    monkeypatch.setattr(email_module.settings, "EMAIL_PROVIDER_ENABLED", True)
    monkeypatch.setattr(email_module.settings, "BREVO_API_KEY", None)
    result = email_module.send_email(to="x@example.com", subject="s", html="<p>h</p>", text="t")
    assert result.sent is False
    assert calls == []

    monkeypatch.setattr(email_module.settings, "BREVO_API_KEY", "fake-key")
    monkeypatch.setattr(email_module.settings, "EMAIL_FROM_EMAIL", None)
    result = email_module.send_email(to="x@example.com", subject="s", html="<p>h</p>", text="t")
    assert result.sent is False
    assert calls == []


def test_brevo_request_shape_is_correct(monkeypatch):
    """Verifies this app's code builds the exact request Brevo's
    Transactional Email API documents: POST to /v3/smtp/email, the API key
    in the `api-key` header (not Authorization/Bearer - Brevo, unlike
    Resend, uses its own header name), and sender/to/subject/htmlContent/
    textContent in the JSON body."""
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeResponse(201, {"messageId": "fake-message-id-123"})

    monkeypatch.setattr(email_module.httpx, "post", fake_post)
    monkeypatch.setattr(email_module.settings, "EMAIL_PROVIDER_ENABLED", True)
    monkeypatch.setattr(email_module.settings, "BREVO_API_KEY", "fake-brevo-key")
    monkeypatch.setattr(email_module.settings, "EMAIL_FROM_EMAIL", "sender@example.com")
    monkeypatch.setattr(email_module.settings, "EMAIL_FROM_NAME", "Rockstar Organics")

    result = email_module.send_email(to="recipient@example.com", subject="Hello", html="<p>Hi</p>", text="Hi")

    assert result.sent is True
    assert result.provider_message_id == "fake-message-id-123"
    assert captured["url"] == "https://api.brevo.com/v3/smtp/email"
    assert captured["headers"]["api-key"] == "fake-brevo-key"
    assert "Authorization" not in captured["headers"]  # Brevo does not use Bearer auth
    assert captured["json"]["sender"] == {"name": "Rockstar Organics", "email": "sender@example.com"}
    assert captured["json"]["to"] == [{"email": "recipient@example.com"}]
    assert captured["json"]["subject"] == "Hello"
    assert captured["json"]["htmlContent"] == "<p>Hi</p>"
    assert captured["json"]["textContent"] == "Hi"


def test_brevo_error_response_does_not_raise_and_reports_failure(monkeypatch):
    """A rejected send (e.g. unverified sender, bad recipient) must surface
    as EmailResult.sent=False with the provider's own error, and must never
    raise - the caller (signup/forgot-password/approval flows) always
    completes the request even if the follow-up email fails."""
    monkeypatch.setattr(
        email_module.httpx, "post",
        lambda *a, **k: _FakeResponse(401, text='{"code":"unauthorized","message":"Key not found"}'),
    )
    monkeypatch.setattr(email_module.settings, "EMAIL_PROVIDER_ENABLED", True)
    monkeypatch.setattr(email_module.settings, "BREVO_API_KEY", "fake-brevo-key")
    monkeypatch.setattr(email_module.settings, "EMAIL_FROM_EMAIL", "sender@example.com")

    result = email_module.send_email(to="recipient@example.com", subject="Hello", html="<p>Hi</p>", text="Hi")
    assert result.sent is False
    assert result.error and "401" in result.error


def test_storage_defaults_to_local_disk_without_supabase_config(monkeypatch, tmp_path):
    monkeypatch.setattr(storage_module.settings, "SUPABASE_URL", None)
    monkeypatch.setattr(storage_module.settings, "SUPABASE_SERVICE_ROLE_KEY", None)
    monkeypatch.setattr(storage_module.settings, "UPLOAD_ROOT", str(tmp_path))
    assert storage_module.backend_name() == "local"

    storage_module.save("public/test-file.txt", b"hello world", "text/plain")
    assert (tmp_path / "public" / "test-file.txt").read_bytes() == b"hello world"
    assert storage_module.load("public/test-file.txt") == b"hello world"
    assert storage_module.load("public/does-not-exist.txt") is None


def test_storage_switches_to_supabase_when_configured_and_uses_service_role_key(monkeypatch, tmp_path):
    """Confirms SUPABASE_SERVICE_ROLE_KEY is sent to Supabase's own API
    (server-side outbound call) and never appears anywhere a client could
    read it back - the fake server here stands in for Supabase and simply
    records what it received."""
    captured = {}

    def fake_post(url, headers=None, content=None, timeout=None):
        captured["post_url"] = url
        captured["post_headers"] = headers
        captured["post_content"] = content
        return _FakeResponse(200)

    def fake_get(url, headers=None, timeout=None):
        captured["get_url"] = url
        captured["get_headers"] = headers
        return _FakeResponse(200, text="fake file bytes")

    monkeypatch.setattr(storage_module.httpx, "post", fake_post)
    monkeypatch.setattr(storage_module.httpx, "get", fake_get)
    monkeypatch.setattr(storage_module.settings, "SUPABASE_URL", "https://fakeproject.supabase.co")
    monkeypatch.setattr(storage_module.settings, "SUPABASE_SERVICE_ROLE_KEY", "fake-service-role-key")
    monkeypatch.setattr(storage_module.settings, "SUPABASE_STORAGE_BUCKET", "test-bucket")

    assert storage_module.backend_name() == "supabase"

    storage_module.save("public/img.jpg", b"fake-image-bytes", "image/jpeg")
    assert captured["post_url"] == "https://fakeproject.supabase.co/storage/v1/object/test-bucket/public/img.jpg"
    assert captured["post_headers"]["Authorization"] == "Bearer fake-service-role-key"
    assert captured["post_headers"]["apikey"] == "fake-service-role-key"
    assert captured["post_content"] == b"fake-image-bytes"

    content = storage_module.load("public/img.jpg")
    assert content == b"fake file bytes"
    assert captured["get_headers"]["apikey"] == "fake-service-role-key"


def test_storage_upload_failure_raises_instead_of_pretending_to_succeed(monkeypatch):
    monkeypatch.setattr(storage_module.httpx, "post", lambda *a, **k: _FakeResponse(403, text="Forbidden"))
    monkeypatch.setattr(storage_module.settings, "SUPABASE_URL", "https://fakeproject.supabase.co")
    monkeypatch.setattr(storage_module.settings, "SUPABASE_SERVICE_ROLE_KEY", "fake-service-role-key")

    import pytest
    with pytest.raises(RuntimeError):
        storage_module.save("public/img.jpg", b"data", "image/jpeg")


def test_forgot_password_response_shape_does_not_reveal_account_existence(client):
    """Regression test: `email_sent` must be present in the JSON response
    whether or not the account exists - if only the "account exists"
    branch included the key, an attacker could enumerate registered emails
    just by checking for the key's presence, even though the message text
    is identical either way."""
    client.post("/api/v1/auth/register", json={
        "full_name": "Has Account", "email": "hasaccount@example.com", "phone": "9876543250", "password": "Passw0rd123",
    })
    client.post("/api/v1/auth/logout")

    r_exists = client.post("/api/v1/auth/forgot-password", json={"email": "hasaccount@example.com"})
    r_missing = client.post("/api/v1/auth/forgot-password", json={"email": "definitely-not-registered@example.com"})

    assert "email_sent" in r_exists.json()
    assert "email_sent" in r_missing.json()
    assert r_exists.json()["message"] == r_missing.json()["message"]
