"""
Vercel serverless entrypoint.

Vercel's Python runtime looks for an ASGI-compatible `app` object exported
from a file under `api/`. The real application lives in `app/main.py`
(unchanged - this file adds no logic of its own, it just re-exports it) so
the exact same code runs here, under Docker, and under plain `uvicorn`.
"""
from app.main import app  # noqa: F401
