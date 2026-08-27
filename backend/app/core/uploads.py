"""
Secure file upload handling.

Validates extension, declared MIME type, and file signature (magic bytes)
before ever writing to disk; generates a random safe filename (never trusts
the client-supplied name for the stored path); and stores public vs.
private uploads under separate roots so a private file is never reachable
through the public static route.
"""
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import get_settings

settings = get_settings()

IMAGE_TYPES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
}
PDF_TYPE = {"application/pdf": (b"%PDF",)}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DOCUMENT_EXTENSIONS = IMAGE_EXTENSIONS | {".pdf"}

# Explicitly rejected regardless of any other check.
BLOCKED_EXTENSIONS = {".exe", ".sh", ".bat", ".cmd", ".html", ".htm", ".js", ".php", ".svg", ".py"}


def _allowed_types(allow_pdf: bool) -> dict[str, tuple[bytes, ...]]:
    types = dict(IMAGE_TYPES)
    if allow_pdf:
        types.update(PDF_TYPE)
    return types


def _ensure_dirs() -> None:
    Path(settings.UPLOAD_ROOT, settings.PUBLIC_UPLOAD_SUBDIR).mkdir(parents=True, exist_ok=True)
    Path(settings.UPLOAD_ROOT, settings.PRIVATE_UPLOAD_SUBDIR).mkdir(parents=True, exist_ok=True)


def validate_and_store(
    file: UploadFile,
    *,
    is_public: bool,
    allow_pdf: bool,
    max_size_bytes: int,
) -> tuple[str, str, str, int]:
    """Returns (relative_file_path, original_filename, content_type, size_bytes).
    Raises HTTPException(400) on any validation failure."""
    _ensure_dirs()

    original_name = file.filename or "upload"
    ext = Path(original_name).suffix.lower()
    allowed_ext = DOCUMENT_EXTENSIONS if allow_pdf else IMAGE_EXTENSIONS
    if ext in BLOCKED_EXTENSIONS or ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"File type '{ext or 'unknown'}' is not allowed.")

    declared_type = file.content_type or ""
    allowed = _allowed_types(allow_pdf)
    if declared_type not in allowed:
        raise HTTPException(status_code=400, detail=f"Content type '{declared_type}' is not allowed.")

    content = file.file.read(max_size_bytes + 1)
    if len(content) > max_size_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds the maximum allowed size of {max_size_bytes // (1024*1024)}MB.")
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    signatures = allowed[declared_type]
    if not any(content.startswith(sig) for sig in signatures):
        raise HTTPException(status_code=400, detail="File content does not match its declared type.")

    safe_name = f"{uuid.uuid4().hex}{ext}"
    subdir = settings.PUBLIC_UPLOAD_SUBDIR if is_public else settings.PRIVATE_UPLOAD_SUBDIR
    dest_dir = Path(settings.UPLOAD_ROOT, subdir)
    dest_path = dest_dir / safe_name
    with open(dest_path, "wb") as f:
        f.write(content)

    relative_path = f"{subdir}/{safe_name}"
    return relative_path, os.path.basename(original_name)[:255], declared_type, len(content)
