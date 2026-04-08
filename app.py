# Root-level app.py — kept for local dev/debugging only.
# Docker runs server/app.py via: uvicorn server.app:app
from server.app import app  # noqa: F401 — re-export for convenience