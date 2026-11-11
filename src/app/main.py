"""FastAPI application shared by the Cloudflare ASGI entry and local uvicorn."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response

from app.api.routes import (
    admin_router,
    attachment_router,
    auth_router,
    category_router,
    cost_router,
    inbox_router,
    project_router,
    stats_router,
    task_router,
)
from app.blobs import R2BlobStore
from app.bootstrap import ensure_ready
from app.db import D1Database
from app.settings import settings_from_worker_env

log = logging.getLogger("personal_pm")
APP_VERSION = "0.1.0"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Personal PM Web",
        version=APP_VERSION,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        parts = []
        for error in exc.errors():
            loc = ".".join(str(item) for item in error.get("loc", []) if item != "body")
            message = error.get("msg", "无效")
            parts.append(f"{loc}: {message}" if loc else message)
        return JSONResponse(status_code=422, content={"detail": "; ".join(parts) or "请求无效"})

    @app.middleware("http")
    async def bind_runtime(request: Request, call_next):
        # HTML, JS, and CSS must not open D1. On Workers those paths are served
        # by static assets; this also covers local files and a Worker that is
        # still invoked for a non-API GET.
        if not request.url.path.startswith("/api"):
            return await call_next(request)
        try:
            _bind_request(request)
            await ensure_ready(request.state.db, request.state.settings)
        except Exception as exc:
            log.exception("failed to bind request runtime")
            return JSONResponse(status_code=500, content={"detail": f"服务初始化失败: {exc}"})
        return await call_next(request)

    @app.get("/api/health")
    async def health(request: Request):
        await request.state.db.fetch_one("SELECT 1 AS ok")
        return {"status": "ok"}

    @app.get("/api/version")
    async def version():
        return {"version": APP_VERSION, "build_time": "2026-11-05"}

    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(project_router)
    app.include_router(task_router)
    app.include_router(cost_router)
    app.include_router(inbox_router)
    app.include_router(category_router)
    app.include_router(attachment_router)
    app.include_router(stats_router)

    @app.api_route("/", methods=["GET", "HEAD"])
    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
    async def spa(request: Request, full_path: str = ""):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(404, "Not found")
        if ".." in full_path.split("/"):
            raise HTTPException(400, "bad path")
        env = request.scope.get("env")
        if env is not None:
            return await _worker_asset(env, full_path, request.method)
        dist = getattr(request.app.state, "dist", None)
        if dist:
            target = _local_asset(Path(dist), full_path)
            if target is not None:
                if request.method == "HEAD":
                    return Response(status_code=200, media_type=_guess_type(target))
                return FileResponse(target)
        return JSONResponse(
            status_code=404,
            content={"detail": "前端尚未构建。在 frontend 目录执行 npm ci && npm run build。"},
        )

    return app


def _bind_request(request: Request) -> None:
    env = request.scope.get("env")
    if env is not None:
        request.state.db = D1Database(env.DB)
        request.state.blobs = R2BlobStore(env.ATTACHMENTS)
        request.state.settings = settings_from_worker_env(env)
        return
    database = getattr(request.app.state, "db", None)
    blobs = getattr(request.app.state, "blobs", None)
    settings = getattr(request.app.state, "settings", None)
    if database is None or blobs is None or settings is None:
        raise RuntimeError("local database is not configured")
    request.state.db = database
    request.state.blobs = blobs
    request.state.settings = settings


def _local_asset(dist: Path, full_path: str) -> Path | None:
    root = dist.resolve()
    relative = full_path.lstrip("/")
    candidate = root / "index.html" if not relative else (root / relative).resolve()
    if candidate != root and root not in candidate.parents and candidate != root / "index.html":
        return None
    if candidate.is_file():
        return candidate
    if relative and Path(relative).suffix:
        return None
    index = root / "index.html"
    return index if index.is_file() else None


def _guess_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".html": "text/html",
        ".js": "text/javascript",
        ".css": "text/css",
        ".svg": "image/svg+xml",
        ".json": "application/json",
        ".png": "image/png",
        ".webp": "image/webp",
        ".woff2": "font/woff2",
    }.get(suffix, "application/octet-stream")


async def _worker_asset(env, full_path: str, method: str) -> Response:
    relative = full_path.lstrip("/") or "index.html"
    fetched = await _fetch_asset(env, relative)
    status = int(getattr(fetched, "status", 200))
    if status == 404 and "." not in relative.rsplit("/", 1)[-1]:
        fetched = await _fetch_asset(env, "index.html")
        status = int(getattr(fetched, "status", 200))
    body = await fetched.bytes()
    if method == "HEAD":
        body = b""
    media = "application/octet-stream"
    try:
        media = fetched.headers.get("content-type") or media
    except Exception:
        media = "application/octet-stream"
    return Response(content=body, status_code=status, media_type=str(media).split(";")[0].strip())


async def _fetch_asset(env, path: str):
    result = env.ASSETS.fetch(f"https://assets.local/{path}")
    if hasattr(result, "__await__"):
        result = await result
    return result


app = create_app()
