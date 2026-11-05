"""Runtime settings.

Production values come from Worker vars and secrets. Local uvicorn reads the
same names from the environment after `.dev.vars` is loaded.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    jwt_secret: str
    admin_email: str
    admin_password_hash: str | None
    cookie_name: str = "pm_session"
    token_ttl_seconds: int = 7 * 24 * 3600


def _clean(value: str | None, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def settings_from_mapping(values: dict[str, str]) -> Settings:
    email = _clean(values.get("ADMIN_EMAIL"), "leondoubao@hotmail.com").lower()
    password_hash = _clean(values.get("ADMIN_PASSWORD_HASH")) or None
    return Settings(
        jwt_secret=_clean(values.get("JWT_SECRET")),
        admin_email=email,
        admin_password_hash=password_hash,
    )


def settings_from_environ() -> Settings:
    return settings_from_mapping(dict(os.environ))


def settings_from_worker_env(env) -> Settings:
    values: dict[str, str] = {}
    for name in ("JWT_SECRET", "ADMIN_EMAIL", "ADMIN_PASSWORD_HASH"):
        raw = None
        try:
            raw = getattr(env, name)
        except Exception:
            raw = None
        if raw is None:
            try:
                raw = env[name]
            except Exception:
                raw = None
        if raw is not None:
            values[name] = str(raw)
    return settings_from_mapping(values)
