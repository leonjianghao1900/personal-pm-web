"""Idempotent schema apply and bootstrap admin insert.

Workers builds a new D1 handle on every request. Readiness must be keyed by
the database (file path, or the single Worker D1 binding), not by id(db),
or every request replays the full CREATE script. That burst is what exhausts
the Free-plan CPU budget and D1's short-window query limit.
"""

from __future__ import annotations

import asyncio
import logging

from app.schema import SCHEMA_SQL, SCHEMA_VERSION
from app.settings import Settings
from app.util import utcnow

log = logging.getLogger("personal_pm.bootstrap")

# schema version applied, keyed by database identity (not the Python wrapper).
_ready: dict[str, int] = {}
# databases whose bootstrap admin row has already been checked this process.
_admin_ready: set[str] = set()
_locks: dict[str, tuple[asyncio.AbstractEventLoop, asyncio.Lock]] = {}


def _ready_key(db) -> str:
    path = getattr(db, "path", None)
    if path and path != ":memory:":
        return f"sqlite:{path}"
    if path == ":memory:":
        # Each connection is a separate empty database.
        return f"memory:{id(db)}"
    return "d1"


def _lock_for(key: str) -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    current = _locks.get(key)
    if current is None or current[0] is not loop:
        current = (loop, asyncio.Lock())
        _locks[key] = current
    return current[1]


def _schema_missing(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "no such table" in text or "no such column" in text


async def _schema_version(db) -> int | None:
    try:
        row = await db.fetch_one("SELECT version FROM schema_migrations WHERE id = 1")
    except Exception as exc:
        if _schema_missing(exc):
            return None
        raise
    if not row or row.get("version") is None:
        return None
    return int(row["version"])


async def ensure_ready(db, settings: Settings) -> None:
    key = _ready_key(db)
    if _ready.get(key) != SCHEMA_VERSION or key not in _admin_ready:
        async with _lock_for(key):
            if _ready.get(key) != SCHEMA_VERSION:
                if await _schema_version(db) != SCHEMA_VERSION:
                    await db.exec_script(SCHEMA_SQL)
                    await db.execute(
                        """
                        INSERT INTO schema_migrations (id, version) VALUES (1, ?)
                        ON CONFLICT(id) DO UPDATE SET version = excluded.version
                        """,
                        (SCHEMA_VERSION,),
                    )
                _ready[key] = SCHEMA_VERSION
            if key not in _admin_ready and await ensure_admin(db, settings):
                _admin_ready.add(key)


async def ensure_admin(db, settings: Settings) -> bool:
    """Insert the bootstrap admin when missing.

    Returns False when the email or hash is not configured, so a later request
    in the same process can still insert the row. A completed check is cached.
    """
    email = (settings.admin_email or "").strip().lower()
    if not email or not settings.admin_password_hash:
        return False
    existing = await db.fetch_one("SELECT id FROM users WHERE email = ?", (email,))
    if existing:
        return True
    now = utcnow()
    try:
        await db.execute(
            """
            INSERT INTO users (
              email, password_hash, display_name, role, workspace_id,
              must_rotate_password, created_at, updated_at
            ) VALUES (?, ?, ?, 'admin', NULL, 1, ?, ?)
            """,
            (email, settings.admin_password_hash, "管理员", now, now),
        )
    except Exception:
        existing = await db.fetch_one("SELECT id FROM users WHERE email = ?", (email,))
        if not existing:
            log.exception("bootstrap admin insert failed")
            raise
    return True
