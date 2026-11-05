from fastapi.testclient import TestClient
from openpyxl import load_workbook
import io

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, login


def _workspace_client(app) -> TestClient:
    admin = TestClient(app)
    admin.__enter__()
    login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
    workspace = admin.post("/api/admin/workspaces", json={"name": "日常"}).json()
    admin.patch(f"/api/admin/users/{admin.get('/api/auth/me').json()['id']}", json={
        "workspace_id": workspace["id"],
    })
    return admin


def test_projects_tasks_dependencies_costs_inbox_and_excel(app):
    client = _workspace_client(app)
    try:
        project = client.post("/api/projects", json={
            "name": "装修",
            "color": "#0071e3",
            "description": "客厅",
            "start_date": "2026-11-01",
            "end_date": "2026-11-30",
        }).json()
        pid = project["id"]
        parent = client.post(f"/api/projects/{pid}/tasks", json={
            "name": "设计",
            "start_date": "2026-11-01",
            "end_date": "2026-11-05",
            "status": "done",
            "progress": 100,
        }).json()
        child = client.post(f"/api/projects/{pid}/tasks", json={
            "name": "施工",
            "parent_id": parent["id"],
            "start_date": "2026-11-06",
            "end_date": "2026-11-20",
            "status": "progress",
        }).json()
        cycle = client.patch(f"/api/tasks/{parent['id']}", json={"parent_id": child["id"]})
        assert cycle.status_code == 409

        dependency = client.post(f"/api/tasks/{child['id']}/dependencies", json={
            "predecessor_id": parent["id"],
        })
        assert dependency.status_code == 201, dependency.text
        again = client.post(f"/api/tasks/{child['id']}/dependencies", json={
            "predecessor_id": parent["id"],
        })
        assert again.status_code == 200
        loop = client.post(f"/api/tasks/{parent['id']}/dependencies", json={
            "predecessor_id": child["id"],
        })
        assert loop.status_code == 400

        cost = client.post("/api/costs", json={
            "project_id": pid,
            "task_id": child["id"],
            "name": "水泥",
            "category": "材料",
            "amount": 120.5,
            "spent_at": "2026-11-06",
        })
        assert cost.status_code == 201, cost.text
        renamed = client.patch(
            f"/api/cost-categories/{_category_id(client, '材料')}",
            json={"name": "主材"},
        )
        assert renamed.status_code == 200, renamed.text
        assert client.get(f"/api/projects/{pid}/costs").json()[0]["category"] == "主材"
        blocked = client.delete(f"/api/cost-categories/{renamed.json()['id']}")
        assert blocked.status_code == 409

        inbox = client.post("/api/inbox", json={"title": "买灯具", "kind": "idea", "priority": "high"}).json()
        promoted = client.post(f"/api/inbox/{inbox['id']}/promote", json={"project_id": pid, "name": "灯具"})
        assert promoted.status_code == 200, promoted.text
        assert promoted.json()["status"] == "archived"
        assert promoted.json()["promoted_task_id"]

        overview = client.get("/api/stats/overview").json()
        assert overview["project_count"] == 1
        assert overview["active_task_count"] >= 1
        assert overview["this_month_cost"] == 120.5
        assert overview["projects"][0]["task_total"] == 3

        stats = client.get("/api/stats/costs", params={"project_id": pid}).json()
        assert stats["count"] == 1
        assert stats["by_category"]["主材"] == 120.5

        workbook = client.get(f"/api/projects/{pid}/export")
        assert workbook.status_code == 200
        assert workbook.content[:2] == b"PK"
        book = load_workbook(io.BytesIO(workbook.content))
        assert book.sheetnames == ["项目概览", "任务清单", "费用记录", "甘特图"]
    finally:
        client.__exit__(None, None, None)


def _category_id(client: TestClient, name: str) -> int:
    for row in client.get("/api/cost-categories").json():
        if row["name"] == name:
            return row["id"]
    raise AssertionError(name)
