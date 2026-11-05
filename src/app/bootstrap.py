"""Idempotent schema apply and bootstrap admin insert."""

from __future__ import annotations

import logging

from app.schema import SCHEMA_SQL, SCHEMA_VERSION
from app.settings import Settings
from app.util import utcnow

log = logging.getLogger("personal_pm.bootstrap")

_ready: dict[int, int] = {}


async def ensure_ready(db, settings: Settings) -> None:
    if _ready.get(id(db)) != SCHEMA_VERSION:
        await db.exec_script(SCHEMA_SQL)
        await db.execute(
            """
            INSERT INTO schema_migrations (id, version) VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET version = excluded.version
            """,
            (SCHEMA_VERSION,),
        )
        _ready[id(db)] = SCHEMA_VERSION
    await ensure_admin(db, settings)


async def ensure_admin(db, settings: Settings) -> None:
    email = (settings.admin_email or "").strip().lower()
    if not email or not settings.admin_password_hash:
        return
    existing = await db.fetch_one("SELECT id FROM users WHERE email = ?", (email,))
    if existing:
        return
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
