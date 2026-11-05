import asyncio

from fastapi.testclient import TestClient

from app.authutil import hash_password, hash_password_sync, verify_password
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, login


def test_password_hash_roundtrip():
    stored = asyncio.run(hash_password("correct horse battery"))
    assert stored.startswith("pbkdf2_sha256$100000$")
    assert asyncio.run(verify_password("correct horse battery", stored))
    assert not asyncio.run(verify_password("wrong horse battery", stored))
    assert not asyncio.run(verify_password("correct horse battery", None))
    synced = hash_password_sync("correct horse battery", salt=bytes.fromhex(stored.split("$")[2]))
    assert synced == stored


def test_login_me_logout_and_password_rotation(client: TestClient):
    denied = client.get("/api/projects")
    assert denied.status_code == 401

    user = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert user["email"] == ADMIN_EMAIL
    assert user["role"] == "admin"
    assert user["must_rotate_password"] is True
    assert "pm_session" in client.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == user["id"]

    bad = client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": "nope-nope-nope"})
    assert bad.status_code == 401

    rotated = client.post("/api/auth/change-password", json={
        "current_password": ADMIN_PASSWORD,
        "new_password": "replacement-pass-1",
    })
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["must_rotate_password"] is False

    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD,
    }).status_code == 401
    assert login(client, ADMIN_EMAIL, "replacement-pass-1")["must_rotate_password"] is False


def test_user_cannot_call_admin_and_must_have_workspace(app):
    with TestClient(app) as admin, TestClient(app) as user_client:
        login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
        created = admin.post("/api/admin/workspaces", json={"name": "默认"})
        assert created.status_code == 201, created.text
        workspace_id = created.json()["id"]
        categories = created
        assert categories.json()["member_count"] == 0

        missing = admin.post("/api/admin/users", json={
            "email": "plain@example.com",
            "password": "plain-pass-123",
            "role": "user",
        })
        assert missing.status_code == 400

        made = admin.post("/api/admin/users", json={
            "email": "plain@example.com",
            "password": "plain-pass-123",
            "role": "user",
            "workspace_id": workspace_id,
        })
        assert made.status_code == 201, made.text
        login(user_client, "plain@example.com", "plain-pass-123")
        assert user_client.get("/api/admin/users").status_code == 403
        assert user_client.get("/api/admin/workspaces").status_code == 403
        listed = user_client.get("/api/cost-categories")
        assert listed.status_code == 200
        names = {row["name"] for row in listed.json()}
        assert names == {"材料", "人工", "差旅", "其他"}
        assert all(row["is_builtin"] is True for row in listed.json())
