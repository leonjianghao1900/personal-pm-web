"""Local ASGI server: SQLite stands in for D1, a directory stands in for R2."""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn

from app.blobs import LocalBlobStore
from app.db import SqliteDatabase
from app.local_secrets import ensure_local_secrets
from app.main import create_app
from app.settings import settings_from_environ

ROOT = Path(__file__).resolve().parents[2]


def load_dev_vars(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key and not os.environ.get(key):
            os.environ[key] = value.strip().strip('"').strip("'")


def main() -> None:
    ensure_local_secrets(ROOT)
    load_dev_vars(ROOT / ".dev.vars")
    data = ROOT / "data"
    data.mkdir(parents=True, exist_ok=True)
    application = create_app()
    application.state.db = SqliteDatabase(str(data / "pm.sqlite"))
    application.state.blobs = LocalBlobStore(data / "blobs")
    application.state.settings = settings_from_environ()
    dist = ROOT / "frontend" / "dist"
    application.state.dist = dist if (dist / "index.html").is_file() else None
    port = int(os.environ.get("PORT", "43123"))
    uvicorn.run(application, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
