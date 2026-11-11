"""Schema bootstrap must not replay DDL on every request handle.

Workers constructs a new D1 wrapper per request. Keying readiness on id(db)
re-ran the full CREATE script for every asset and API call.
"""

import asyncio

from fastapi.testclient import TestClient

from app.bootstrap import _admin_ready, _ready, ensure_ready
from app.db import SqliteDatabase
from app.main import create_app
from app.schema import SCHEMA_VERSION
from app.settings import Settings
from app.util import worker_request_path


def _settings() -> Settings:
    return Settings(
        jwt_secret="test-secret-test-secret-test-secret",
        admin_email="admin@example.com",
        admin_password_hash="pbkdf2_sha256$1$00$00",
    )


def _reset() -> None:
    _ready.clear()
    _admin_ready.clear()


class Counting(SqliteDatabase):
    def __init__(self, path: str):
        super().__init__(path)
        self.scripts = 0
        self.reads = 0

    async def exec_script(self, sql: str) -> None:
        self.scripts += 1
        await super().exec_script(sql)

    async def fetch_one(self, sql: str, params: tuple | list = ()):
        self.reads += 1
        return await super().fetch_one(sql, params)


def test_new_handle_does_not_replay_schema(tmp_path):
    _reset()
    path = str(tmp_path / "pm.sqlite")
    settings = _settings()

    async def run():
        first = Counting(path)
        await ensure_ready(first, settings)
        # Same file, new wrapper: this is what each Worker request does.
        second = Counting(path)
        await ensure_ready(second, settings)
        # New isolate against an already-migrated database: one version read, no DDL.
        _ready.clear()
        _admin_ready.clear()
        third = Counting(path)
        await ensure_ready(third, settings)
        warmed = third.reads
        admin = await third.fetch_one(
            "SELECT email, role FROM users WHERE email = ?",
            (settings.admin_email,),
        )
        version = await third.fetch_one("SELECT version FROM schema_migrations WHERE id = 1")
        return first, second, third, warmed, admin, version

    first, second, third, warmed, admin, version = asyncio.run(run())
    assert first.scripts == 1
    assert second.scripts == 0
    assert second.reads == 0
    assert third.scripts == 0
    # version row, then the bootstrap admin lookup. No DDL.
    assert warmed == 2
    assert admin["role"] == "admin"
    assert int(version["version"]) == SCHEMA_VERSION
    _reset()


def test_separate_databases_each_get_schema(tmp_path):
    _reset()
    settings = _settings()

    async def run():
        west = Counting(str(tmp_path / "west.sqlite"))
        east = Counting(str(tmp_path / "east.sqlite"))
        await ensure_ready(west, settings)
        await ensure_ready(east, settings)
        return west.scripts, east.scripts

    west_scripts, east_scripts = asyncio.run(run())
    assert west_scripts == 1
    assert east_scripts == 1
    _reset()


def test_worker_routes_only_api_into_python():
    assert worker_request_path("https://personal-pm-web.leondoubao.workers.dev/api/auth/me") == "/api/auth/me"
    assert worker_request_path("https://personal-pm-web.leondoubao.workers.dev/assets/index-abc.js") == "/assets/index-abc.js"
    assert worker_request_path("https://personal-pm-web.leondoubao.workers.dev/login") == "/login"
    assert worker_request_path("/api/stats/overview") == "/api/stats/overview"
    assert worker_request_path("[object Object]") == "/api"


def test_pages_do_not_open_the_database():
    _reset()
    app = create_app()
    with TestClient(app) as client:
        page = client.get("/login")
        assert page.status_code == 404
        assert "前端" in page.json()["detail"]
        health = client.get("/api/health")
        assert health.status_code == 500
        assert "初始化" in health.json()["detail"]
