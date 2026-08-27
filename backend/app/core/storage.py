"""
Pluggable file storage backend.

Local disk (default - used automatically whenever Supabase Storage is not
configured, e.g. every local dev/test run) vs. Supabase Storage (used once
SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are both set), so uploaded files
survive redeploys/restarts instead of living on the app server's ephemeral
filesystem. Same "explicit opt-in, transparent fallback" rule as
app/core/email.py: without both settings, this quietly behaves exactly as
it always did (local disk) rather than pretending files are durable when
they aren't.

The Supabase bucket is kept private end-to-end: every read goes through
this module using the service_role key and is streamed back by the FastAPI
route that already enforces this app's own access rules (see
app/routers/media.py) - a "public" upload is public because our own routes
serve it to anyone, not because the object store's URL is guessable.
"""
import logging
from pathlib import Path

import httpx

from app.core.config import get_settings

logger = logging.getLogger("rockstar_organics")
settings = get_settings()


def backend_name() -> str:
    return "supabase" if (settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY) else "local"


def _local_path(relative_path: str) -> Path:
    return Path(settings.UPLOAD_ROOT) / relative_path


def _supabase_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
    }


def save(relative_path: str, content: bytes, content_type: str) -> None:
    """Persists `content` at `relative_path` (e.g. "public/<uuid>.jpg").
    Raises RuntimeError if the Supabase backend rejects the upload - callers
    should let this propagate as a 500 rather than silently losing the
    file, since (unlike email) a failed upload should not appear to have
    succeeded."""
    if backend_name() == "supabase":
        url = f"{settings.SUPABASE_URL}/storage/v1/object/{settings.SUPABASE_STORAGE_BUCKET}/{relative_path}"
        response = httpx.post(
            url,
            headers={**_supabase_headers(), "Content-Type": content_type, "x-upsert": "true"},
            content=content,
            timeout=30.0,
        )
        if response.status_code >= 400:
            logger.warning('{"message": "Supabase Storage upload failed", "path": "%s", "status": %s}', relative_path, response.status_code)
            raise RuntimeError(f"Storage upload failed ({response.status_code}): {response.text[:300]}")
        return

    path = _local_path(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)


def load(relative_path: str) -> bytes | None:
    """Returns the file's bytes, or None if it does not exist (never raises
    for a missing file - callers turn that into a 404)."""
    if backend_name() == "supabase":
        url = f"{settings.SUPABASE_URL}/storage/v1/object/{settings.SUPABASE_STORAGE_BUCKET}/{relative_path}"
        response = httpx.get(url, headers=_supabase_headers(), timeout=30.0)
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            logger.warning('{"message": "Supabase Storage download failed", "path": "%s", "status": %s}', relative_path, response.status_code)
            return None
        return response.content

    path = _local_path(relative_path)
    if not path.exists() or not path.is_file():
        return None
    return path.read_bytes()
