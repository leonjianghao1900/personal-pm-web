"""Create the gitignored bootstrap password and local Worker secrets once.

The plaintext password is written only to artifacts/ADMIN_INITIAL_PASSWORD.txt.
`.dev.vars` receives the PBKDF2 hash and the JWT signing secret, never the
password itself.
"""

from __future__ import annotations

import secrets
import stat
from pathlib import Path

from app.authutil import hash_password_sync as hash_password

ADMIN_EMAIL = "leondoubao@hotmail.com"


def ensure_local_secrets(root: Path) -> None:
    artifacts = root / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    password_path = artifacts / "ADMIN_INITIAL_PASSWORD.txt"
    hash_path = artifacts / "ADMIN_PASSWORD_HASH.txt"
    jwt_path = artifacts / "JWT_SECRET.txt"

    password = _read_password(password_path)
    password_hash = _read_single(hash_path)
    if password is None and password_hash is None:
        password = secrets.token_urlsafe(24)
        _write_secret(password_path, _password_document(password))
        password_hash = hash_password(password)
        _write_secret(hash_path, password_hash + "\n")
    elif password is not None and password_hash is None:
        password_hash = hash_password(password)
        _write_secret(hash_path, password_hash + "\n")
    elif password_hash is None:
        raise RuntimeError("admin password hash is missing")

    jwt_secret = _read_single(jwt_path)
    if not jwt_secret:
        jwt_secret = secrets.token_urlsafe(32)
        _write_secret(jwt_path, jwt_secret + "\n")

    dev_vars = root / ".dev.vars"
    _write_secret(
        dev_vars,
        "\n".join([
            f"JWT_SECRET={jwt_secret}",
            f"ADMIN_PASSWORD_HASH={password_hash}",
            f"ADMIN_EMAIL={ADMIN_EMAIL}",
            "",
        ]),
    )
    _mirror_artifacts(password_path, hash_path, jwt_path)


def _password_document(password: str) -> str:
    return (
        "Personal PM Web bootstrap admin\n"
        f"email: {ADMIN_EMAIL}\n"
        f"password: {password}\n"
        "\n"
        "Log in, then change this password under 设置 → 修改密码\n"
        "(or POST /api/auth/change-password). Delete this file after rotating.\n"
        "It is gitignored and must not be committed.\n"
    )


def _read_password(path: Path) -> str | None:
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("password:"):
            value = line.split(":", 1)[1].strip()
            return value or None
    return None


def _read_single(path: Path) -> str | None:
    if not path.is_file():
        return None
    value = path.read_text(encoding="utf-8").strip()
    return value or None


def _write_secret(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def _mirror_artifacts(*paths: Path) -> None:
    mirror = Path("/opt/cursor/artifacts")
    try:
        mirror.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    for path in paths:
        if not path.is_file():
            continue
        target = mirror / path.name
        try:
            _write_secret(target, path.read_text(encoding="utf-8"))
        except OSError:
            continue
