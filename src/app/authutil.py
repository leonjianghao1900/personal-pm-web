"""Password hashing and JWT cookies.

PBKDF2-HMAC-SHA256. CPython uses hashlib.pbkdf2_hmac. Workers Pyodide does
not provide pbkdf2_hmac, so the async helpers use WebCrypto at 100000
iterations (the Workers maximum). hash_password_sync is the local rehash path.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

PBKDF2_ITERATIONS = 100_000  # Workers WebCrypto max is 100000
COOKIE_NAME = "pm_session"


def _hash_format(iterations: int, salt: bytes, digest: bytes) -> str:
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def hash_password_sync(password: str, *, salt: bytes | None = None, iterations: int = PBKDF2_ITERATIONS) -> str:
    """CPython-only (local tooling). Pyodide's hashlib has no pbkdf2_hmac."""
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return _hash_format(iterations, salt, digest)


async def _pbkdf2(password: bytes, salt: bytes, iterations: int) -> bytes:
    if hasattr(hashlib, "pbkdf2_hmac"):
        return hashlib.pbkdf2_hmac("sha256", password, salt, iterations)
    # Workers/Pyodide: use native WebCrypto (fast, outside the Python CPU budget).
    from js import Object, Uint8Array, crypto  # type: ignore
    from pyodide.ffi import to_js  # type: ignore

    key = await crypto.subtle.importKey(
        "raw", to_js(password), "PBKDF2", False, to_js(["deriveBits"])
    )
    params = to_js(
        {"name": "PBKDF2", "hash": "SHA-256", "salt": to_js(salt), "iterations": iterations},
        dict_converter=Object.fromEntries,
    )
    bits = await crypto.subtle.deriveBits(params, key, 256)
    return bytes(Uint8Array.new(bits).to_py())


async def hash_password(password: str, *, salt: bytes | None = None, iterations: int = PBKDF2_ITERATIONS) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = await _pbkdf2(password.encode("utf-8"), salt, iterations)
    return _hash_format(iterations, salt, digest)


async def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        await hash_password(password)
        return False
    try:
        algo, rounds_s, salt_hex, digest_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        rounds = int(rounds_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (TypeError, ValueError):
        return False
    digest = await _pbkdf2(password.encode("utf-8"), salt, rounds)
    return hmac.compare_digest(digest, expected)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def encode_jwt(payload: dict, secret: str) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(secret.encode("utf-8"), f"{header}.{body}".encode("ascii"), hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url(signature)}"


def decode_jwt(token: str, secret: str) -> dict:
    try:
        header, body, signature = token.split(".")
    except ValueError as exc:
        raise ValueError("malformed token") from exc
    expected = hmac.new(secret.encode("utf-8"), f"{header}.{body}".encode("ascii"), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64url_decode(signature)):
        raise ValueError("bad signature")
    payload = json.loads(_b64url_decode(body))
    if int(payload.get("exp", 0)) < int(time.time()):
        raise ValueError("expired")
    return payload


def make_token(user_id: int, secret: str, ttl_seconds: int) -> str:
    now = int(time.time())
    return encode_jwt({"sub": user_id, "iat": now, "exp": now + ttl_seconds}, secret)
