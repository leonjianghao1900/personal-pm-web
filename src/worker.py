"""Cloudflare Python Worker entry.

Static assets are served by this same process (`run_worker_first`) so `/api`
always wins over the Vue build.
"""

from app.main import app
from workers import asgi

Default = asgi.entrypoint(app)
