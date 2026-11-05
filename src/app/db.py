"""Thin SQL access shared by local SQLite and Cloudflare D1.

D1 speaks SQLite. Both adapters normalize parameters and return plain dict
rows so the rest of the app never imports a driver.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import date, datetime, timezone
from typing import Any


def norm_param(value: Any) -> Any:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    return value


def norm_params(params: tuple | list) -> tuple:
    return tuple(norm_param(item) for item in params)


def to_py(value: Any) -> Any:
    """Best-effort conversion of a Workers JsProxy into plain Python."""
    if value is None or isinstance(value, (str, int, float, bool, bytes)):
        return value
    if isinstance(value, dict):
        return {str(key): to_py(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_py(item) for item in value]
    converter = getattr(value, "to_py", None)
    if callable(converter):
        try:
            return to_py(converter())
        except Exception:
            pass
    try:
        keys = list(value.keys())
    except Exception:
        keys = None
    if keys is not None:
        return {str(key): to_py(value[key]) for key in keys}
    return value


class SqliteDatabase:
    def __init__(self, path: str):
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self.conn.execute("PRAGMA foreign_keys = ON")

    def _rows(self, cursor: sqlite3.Cursor) -> list[dict]:
        if cursor.description is None:
            return []
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    async def exec_script(self, sql: str) -> None:
        with self._lock:
            self.conn.executescript(sql)
            self.conn.execute("PRAGMA foreign_keys = ON")

    async def fetch_all(self, sql: str, params: tuple | list = ()) -> list[dict]:
        with self._lock:
            cursor = self.conn.execute(sql, norm_params(params))
            return self._rows(cursor)

    async def fetch_one(self, sql: str, params: tuple | list = ()) -> dict | None:
        rows = await self.fetch_all(sql, params)
        return rows[0] if rows else None

    async def execute(self, sql: str, params: tuple | list = ()) -> tuple[int, int]:
        with self._lock:
            cursor = self.conn.execute(sql, norm_params(params))
            return int(cursor.lastrowid or 0), int(cursor.rowcount if cursor.rowcount is not None else 0)

    async def batch(self, statements: list[tuple[str, tuple | list]]) -> None:
        with self._lock:
            try:
                self.conn.execute("BEGIN IMMEDIATE")
                for sql, params in statements:
                    self.conn.execute(sql, norm_params(params))
                self.conn.execute("COMMIT")
            except Exception:
                try:
                    self.conn.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise


class D1Database:
    """Cloudflare D1 binding. Statements are prepared per call.

    Inserts that need the new id use `RETURNING` and are read with `all()`,
    because each D1 call can land on a different connection and
    `last_insert_rowid()` is not reliable across calls. Multi-statement
    changes that must commit or roll back together go through `batch()`.
    """

    def __init__(self, binding):
        self.binding = binding

    def _statement(self, sql: str, params: tuple | list):
        statement = self.binding.prepare(sql)
        normalized = norm_params(params)
        if normalized:
            statement = statement.bind(*normalized)
        return statement

    async def exec_script(self, sql: str) -> None:
        # D1 exec() treats each newline as a statement boundary, which breaks
        # multi-line CREATE TABLE. Split on ';' and batch prepared statements.
        statements = _split_sql(sql)
        if statements:
            await self.batch([(statement, ()) for statement in statements])

    async def fetch_all(self, sql: str, params: tuple | list = ()) -> list[dict]:
        result = to_py(await self._statement(sql, params).all())
        rows = []
        if isinstance(result, dict):
            rows = result.get("results") or []
        elif isinstance(result, list):
            rows = result
        return [dict(row) for row in rows]

    async def fetch_one(self, sql: str, params: tuple | list = ()) -> dict | None:
        rows = await self.fetch_all(sql, params)
        return rows[0] if rows else None

    async def execute(self, sql: str, params: tuple | list = ()) -> tuple[int, int]:
        result = to_py(await self._statement(sql, params).run())
        meta = {}
        if isinstance(result, dict):
            meta = result.get("meta") or {}
        if not isinstance(meta, dict):
            meta = to_py(meta) or {}
        last_id = int(meta.get("last_row_id") or 0)
        changes = int(meta.get("changes") or meta.get("rows_written") or 0)
        return last_id, changes

    async def batch(self, statements: list[tuple[str, tuple | list]]) -> None:
        prepared = [self._statement(sql, params) for sql, params in statements]
        result = self.binding.batch(prepared)
        if hasattr(result, "__await__"):
            await result


def _split_sql(sql: str) -> list[str]:
    parts = []
    for chunk in sql.split(";"):
        statement = chunk.strip()
        if statement:
            parts.append(statement)
    return parts
