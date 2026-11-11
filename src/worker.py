"""Cloudflare Python Worker entry.

Only `/api/*` runs the FastAPI app. Everything else is returned from the
ASSETS binding without copying the body into Pyodide. wrangler.toml also sets
`run_worker_first` to `/api/*`, so a normal page view never enters this module
at all. The branch below still matters if a request does.
"""

from workers import WorkerEntrypoint
from workers.asgi import fetch as asgi_fetch

from app.main import app
from app.util import worker_request_path


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        if not worker_request_path(getattr(request, "url", "")).startswith("/api"):
            return await self.env.ASSETS.fetch(request)
        return await asgi_fetch(app, request, self.env, self.ctx)
