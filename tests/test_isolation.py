import io
import json
import zipfile

from fastapi.testclient import TestClient

from tests.conftest import bootstrap_two_workspaces, login


def _clients(app):
    admin = TestClient(app)
    west_client = TestClient(app)
    east_client = TestClient(app)
    admin.__enter__()
    west_client.__enter__()
    east_client.__enter__()
    return admin, west_client, east_client


def test_workspace_isolation_for_projects_tasks_and_files(app):
    admin, west_client, east_client = _clients(app)
    try:
        bootstrap_two_workspaces(admin)
        login(west_client, "west@example.com", "west-pass-123")
        login(east_client, "east@example.com", "east-pass-123")

        created = west_client.post("/api/projects", json={"name": "西区项目", "color": "#0071e3"})
        assert created.status_code == 201, created.text
        project_id = created.json()["id"]
        task = west_client.post(f"/api/projects/{project_id}/tasks", json={"name": "地基"})
        assert task.status_code == 201, task.text
        task_id = task.json()["id"]
        upload = west_client.post(
            f"/api/attachments/task/{task_id}",
            files={"file": ("note.txt", b"west-only", "text/plain")},
        )
        assert upload.status_code == 201, upload.text
        attachment_id = upload.json()["id"]

        assert east_client.get("/api/projects").json() == []
        assert east_client.get(f"/api/projects/{project_id}").status_code == 404
        assert east_client.get(f"/api/tasks/{task_id}").status_code == 404
        assert east_client.get(f"/api/attachments/{attachment_id}/download").status_code == 404
        assert west_client.get(f"/api/attachments/{attachment_id}/download").content == b"west-only"

        shared = admin.post("/api/admin/users", json={
            "email": "west2@example.com",
            "password": "west2-pass-123",
            "role": "user",
            "workspace_id": west_client.get("/api/auth/me").json()["workspace_id"],
        })
        assert shared.status_code == 201
        with TestClient(app) as mate:
            login(mate, "west2@example.com", "west2-pass-123")
            assert [row["name"] for row in mate.get("/api/projects").json()] == ["西区项目"]
    finally:
        west_client.__exit__(None, None, None)
        east_client.__exit__(None, None, None)
        admin.__exit__(None, None, None)


def test_backup_restore_does_not_cross_workspaces(app):
    admin, west_client, east_client = _clients(app)
    try:
        bootstrap_two_workspaces(admin)
        login(west_client, "west@example.com", "west-pass-123")
        login(east_client, "east@example.com", "east-pass-123")
        east_project = east_client.post("/api/projects", json={"name": "东区保留"}).json()

        project = west_client.post("/api/projects", json={"name": "要备份"})
        project_id = project.json()["id"]
        task_id = west_client.post(f"/api/projects/{project_id}/tasks", json={"name": "附件任务"}).json()["id"]
        west_client.post(
            f"/api/attachments/task/{task_id}",
            files={"file": ("pic.bin", b"\x00\x01payload", "application/octet-stream")},
        )
        archive = west_client.get("/api/admin/backup/full")
        assert archive.status_code == 200, archive.text
        assert archive.content[:2] == b"PK"

        empty = {
            "version": 3,
            "projects": [],
            "tasks": [],
            "task_dependencies": [],
            "costs": [],
            "cost_categories": [],
            "inbox_items": [],
            "attachments": [],
        }
        wiped = west_client.post(
            "/api/admin/restore",
            files={"file": ("backup.json", json.dumps(empty), "application/json")},
        )
        assert wiped.status_code == 200, wiped.text
        assert west_client.get("/api/projects").json() == []
        assert east_client.get(f"/api/projects/{east_project['id']}").json()["name"] == "东区保留"

        restored = west_client.post(
            "/api/admin/restore/full",
            files={"file": ("backup.zip", archive.content, "application/zip")},
        )
        assert restored.status_code == 200, restored.text
        projects = west_client.get("/api/projects").json()
        assert [row["name"] for row in projects] == ["要备份"]
        restored_task = west_client.get(f"/api/projects/{projects[0]['id']}/tasks").json()[0]
        files = west_client.get(f"/api/attachments/task/{restored_task['id']}").json()
        assert len(files) == 1
        body = west_client.get(f"/api/attachments/{files[0]['id']}/download").content
        assert body == b"\x00\x01payload"
        assert east_client.get("/api/projects").json()[0]["name"] == "东区保留"

        # The zip really contains the object bytes, not only metadata.
        with zipfile.ZipFile(io.BytesIO(archive.content)) as zf:
            names = zf.namelist()
            assert "backup.json" in names
            assert any(name.startswith("attachments/") for name in names)
    finally:
        west_client.__exit__(None, None, None)
        east_client.__exit__(None, None, None)
        admin.__exit__(None, None, None)
