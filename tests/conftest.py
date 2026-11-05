import pytest
from fastapi.testclient import TestClient

from app.authutil import hash_password_sync
from app.blobs import LocalBlobStore
from app.db import SqliteDatabase
from app.main import create_app
from app.settings import Settings

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin-pass-123"


@pytest.fixture
def app(tmp_path):
    application = create_app()
    application.state.db = SqliteDatabase(str(tmp_path / "pm.sqlite"))
    application.state.blobs = LocalBlobStore(tmp_path / "blobs")
    application.state.settings = Settings(
        jwt_secret="test-secret-test-secret-test-secret",
        admin_email=ADMIN_EMAIL,
        admin_password_hash=hash_password_sync(ADMIN_PASSWORD),
    )
    application.state.dist = None
    return application


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def login(test_client: TestClient, email: str, password: str) -> dict:
    response = test_client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["user"]


def bootstrap_two_workspaces(admin: TestClient):
    login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
    west = admin.post("/api/admin/workspaces", json={"name": "西区"}).json()
    east = admin.post("/api/admin/workspaces", json={"name": "东区"}).json()
    admin.post("/api/admin/users", json={
        "email": "west@example.com",
        "password": "west-pass-123",
        "display_name": "西区用户",
        "role": "user",
        "workspace_id": west["id"],
    })
    admin.post("/api/admin/users", json={
        "email": "east@example.com",
        "password": "east-pass-123",
        "display_name": "东区用户",
        "role": "user",
        "workspace_id": east["id"],
    })
    return west, east
