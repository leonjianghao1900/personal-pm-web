"""Attachment bytes. Local files in development, R2 in the Worker."""

from __future__ import annotations

from pathlib import Path

from app.db import to_py


def object_key(workspace_id: int, stored_path: str) -> str:
    return f"ws/{int(workspace_id)}/{stored_path}"


class LocalBlobStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        if not key or key.startswith("/") or ".." in key.split("/"):
            raise ValueError("invalid object key")
        path = (self.root / key).resolve()
        root = self.root.resolve()
        if path != root and root not in path.parents:
            raise ValueError("invalid object key")
        return path

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        del content_type
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    async def get(self, key: str) -> bytes | None:
        path = self._path(key)
        if not path.is_file():
            return None
        return path.read_bytes()

    async def delete_many(self, keys: list[str]) -> None:
        for key in keys:
            path = self._path(key)
            try:
                path.unlink()
            except FileNotFoundError:
                continue


class R2BlobStore:
    def __init__(self, bucket):
        self.bucket = bucket

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        try:
            result = self.bucket.put(key, data, httpMetadata={"contentType": content_type})
        except TypeError:
            result = self.bucket.put(key, data)
        if hasattr(result, "__await__"):
            await result

    async def get(self, key: str) -> bytes | None:
        result = self.bucket.get(key)
        if hasattr(result, "__await__"):
            result = await result
        if result is None:
            return None
        return await _read_body(result)

    async def delete_many(self, keys: list[str]) -> None:
        if not keys:
            return
        for start in range(0, len(keys), 1000):
            chunk = keys[start : start + 1000]
            try:
                result = self.bucket.delete(chunk)
            except TypeError:
                for key in chunk:
                    result = self.bucket.delete(key)
                    if hasattr(result, "__await__"):
                        await result
                continue
            if hasattr(result, "__await__"):
                await result


async def _read_body(obj) -> bytes:
    for name in ("arrayBuffer", "bytes", "text"):
        method = getattr(obj, name, None)
        if method is None:
            continue
        raw = method()
        if hasattr(raw, "__await__"):
            raw = await raw
        data = _as_bytes(raw)
        if data is not None:
            return data
    body = getattr(obj, "body", None)
    if body is not None:
        data = _as_bytes(body)
        if data is not None:
            return data
    data = _as_bytes(obj)
    if data is not None:
        return data
    raise RuntimeError("unable to read object body")


def _as_bytes(raw) -> bytes | None:
    if raw is None:
        return None
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    if hasattr(raw, "to_bytes"):
        try:
            return raw.to_bytes()
        except Exception:
            pass
    converted = to_py(raw)
    if isinstance(converted, (bytes, bytearray)):
        return bytes(converted)
    if isinstance(converted, list) and converted and isinstance(converted[0], int):
        return bytes(converted)
    if isinstance(converted, str):
        return converted.encode("utf-8")
    return None
