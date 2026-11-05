"""Workspace-scoped SQL for auth, admin, and the personal-pm domain."""

from __future__ import annotations

import secrets
from datetime import date, timedelta
from pathlib import Path

from app.authutil import hash_password, verify_password
from app.blobs import object_key
from app.errors import Conflict, PayloadTooLarge
from app.schemas import PRIORITIES
from app.util import chunks, today_local, utcnow

MAX_FILE_BYTES = 20 * 1024 * 1024
ENTITY_LIMITS = {"task": 10, "cost": 5, "inbox": 5}
ENTITY_TABLES = {"task": "tasks", "cost": "costs", "inbox": "inbox_items"}
DEFAULT_CATEGORIES = (
    ("材料", "#ff9500", 0),
    ("人工", "#0071e3", 1),
    ("差旅", "#34c759", 2),
    ("其他", "#8e8e93", 3),
)

USER_PUBLIC = """
SELECT u.id, u.email, u.display_name, u.role, u.workspace_id,
       u.must_rotate_password, u.created_at, w.name AS workspace_name
FROM users u
LEFT JOIN workspaces w ON w.id = u.workspace_id
"""

PROJECT_SELECT = """
SELECT p.id, p.name, p.color, p.description, p.start_date, p.end_date, p.status,
       p.created_at, p.updated_at,
       (SELECT COUNT(*) FROM tasks t
        WHERE t.project_id = p.id AND t.workspace_id = p.workspace_id) AS task_count
FROM projects p
"""

TASK_PUBLIC = """
id, project_id, parent_id, name, description, status, priority,
start_date, end_date, progress, sort_order, is_milestone, created_at, updated_at
"""

COST_PUBLIC = "id, project_id, task_id, name, category, amount, description, spent_at, created_at"
DEP_PUBLIC = "id, predecessor_id, successor_id, dep_type, created_at"
INBOX_PUBLIC = """
id, kind, title, notes, priority, due_at, project_id, promoted_task_id,
status, created_at, completed_at
"""
CATEGORY_PUBLIC = "id, name, color, is_builtin, sort_order"
ATT_PUBLIC = "id, entity_type, entity_id, original_name, mime, size, uploaded_at"


def flag(row: dict | None, *names: str) -> dict | None:
    if row is None:
        return None
    out = dict(row)
    for name in names:
        if name in out and out[name] is not None:
            out[name] = bool(out[name])
    return out


def flag_all(rows: list[dict], *names: str) -> list[dict]:
    return [flag(row, *names) for row in rows]


async def _update(db, table: str, values: dict, where_sql: str, where_params: tuple) -> None:
    if not values:
        return
    assignments = ", ".join(f"{column} = ?" for column in values)
    await db.execute(
        f"UPDATE {table} SET {assignments} WHERE {where_sql}",
        tuple(values.values()) + tuple(where_params),
    )


async def count_admins(db) -> int:
    row = await db.fetch_one("SELECT COUNT(*) AS n FROM users WHERE role = 'admin'")
    return int(row["n"])


async def list_users(db) -> list[dict]:
    return flag_all(
        await db.fetch_all(USER_PUBLIC + " ORDER BY u.id"),
        "must_rotate_password",
    )


async def get_user(db, user_id: int) -> dict | None:
    return flag(
        await db.fetch_one(USER_PUBLIC + " WHERE u.id = ?", (user_id,)),
        "must_rotate_password",
    )


async def get_user_by_email(db, email: str) -> dict | None:
    return await db.fetch_one(
        """
        SELECT u.id, u.email, u.password_hash, u.display_name, u.role, u.workspace_id,
               u.must_rotate_password, u.created_at, w.name AS workspace_name
        FROM users u
        LEFT JOIN workspaces w ON w.id = u.workspace_id
        WHERE u.email = ?
        """,
        (email,),
    )


async def insert_user(db, *, email: str, password: str, display_name: str, role: str, workspace_id: int | None) -> dict:
    if await db.fetch_one("SELECT id FROM users WHERE email = ?", (email,)):
        raise Conflict("邮箱已存在")
    if role != "admin" and workspace_id is None:
        raise ValueError("普通用户必须属于一个工作区")
    if workspace_id is not None and not await get_workspace(db, workspace_id):
        raise ValueError("工作区不存在")
    now = utcnow()
    await db.execute(
        """
        INSERT INTO users (
          email, password_hash, display_name, role, workspace_id,
          must_rotate_password, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """,
        (email, await hash_password(password), display_name, role, workspace_id, now, now),
    )
    row = await db.fetch_one(USER_PUBLIC + " WHERE u.email = ?", (email,))
    return flag(row, "must_rotate_password")


async def update_user(db, user_id: int, changes: dict) -> dict | None:
    current = await get_user(db, user_id)
    if current is None:
        return None
    new_role = changes.get("role", current["role"])
    new_workspace = changes["workspace_id"] if "workspace_id" in changes else current["workspace_id"]
    if new_role != "admin" and new_workspace is None:
        raise ValueError("普通用户必须属于一个工作区")
    if current["role"] == "admin" and new_role != "admin" and await count_admins(db) <= 1:
        raise Conflict("不能取消最后一名管理员")
    if new_workspace is not None and not await get_workspace(db, new_workspace):
        raise ValueError("工作区不存在")
    values: dict = {}
    if "display_name" in changes and changes["display_name"]:
        values["display_name"] = str(changes["display_name"]).strip()
    if "role" in changes:
        values["role"] = new_role
    if "workspace_id" in changes:
        values["workspace_id"] = new_workspace
    if changes.get("password"):
        values["password_hash"] = await hash_password(changes["password"])
        values["must_rotate_password"] = 1
    if values:
        values["updated_at"] = utcnow()
        await _update(db, "users", values, "id = ?", (user_id,))
    return await get_user(db, user_id)


async def delete_user(db, user_id: int, actor_id: int) -> bool:
    user = await get_user(db, user_id)
    if user is None:
        return False
    if user_id == actor_id:
        raise Conflict("不能删除当前登录账号")
    if user["role"] == "admin" and await count_admins(db) <= 1:
        raise Conflict("不能删除最后一名管理员")
    await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return True


async def change_password(db, user_id: int, current_password: str, new_password: str) -> None:
    row = await db.fetch_one("SELECT password_hash FROM users WHERE id = ?", (user_id,))
    if row is None or not await verify_password(current_password, row["password_hash"]):
        raise ValueError("当前密码不正确")
    if await verify_password(new_password, row["password_hash"]):
        raise ValueError("新密码不能与当前密码相同")
    await db.execute(
        """
        UPDATE users
        SET password_hash = ?, must_rotate_password = 0, updated_at = ?
        WHERE id = ?
        """,
        (await hash_password(new_password), utcnow(), user_id),
    )


async def list_workspaces(db) -> list[dict]:
    return await db.fetch_all(
        """
        SELECT w.id, w.name, w.created_at, w.updated_at,
               (SELECT COUNT(*) FROM users u WHERE u.workspace_id = w.id) AS member_count
        FROM workspaces w
        ORDER BY w.id
        """
    )


async def get_workspace(db, workspace_id: int) -> dict | None:
    return await db.fetch_one(
        """
        SELECT w.id, w.name, w.created_at, w.updated_at,
               (SELECT COUNT(*) FROM users u WHERE u.workspace_id = w.id) AS member_count
        FROM workspaces w
        WHERE w.id = ?
        """,
        (workspace_id,),
    )


async def create_workspace(db, name: str) -> dict:
    now = utcnow()
    created = await db.fetch_one(
        """
        INSERT INTO workspaces (name, created_at, updated_at)
        VALUES (?, ?, ?)
        RETURNING id
        """,
        (name.strip(), now, now),
    )
    workspace_id = created["id"]
    for cat_name, color, sort_order in DEFAULT_CATEGORIES:
        await db.execute(
            """
            INSERT INTO cost_categories (workspace_id, name, color, is_builtin, sort_order)
            VALUES (?, ?, ?, 1, ?)
            """,
            (workspace_id, cat_name, color, sort_order),
        )
    return await get_workspace(db, workspace_id)


async def rename_workspace(db, workspace_id: int, name: str) -> dict | None:
    current = await get_workspace(db, workspace_id)
    if current is None:
        return None
    await db.execute(
        "UPDATE workspaces SET name = ?, updated_at = ? WHERE id = ?",
        (name.strip(), utcnow(), workspace_id),
    )
    return await get_workspace(db, workspace_id)


async def delete_workspace(db, blobs, workspace_id: int) -> bool:
    current = await get_workspace(db, workspace_id)
    if current is None:
        return False
    if int(current["member_count"]) > 0:
        raise Conflict("工作区仍有成员，请先把成员调离")
    attachments = await db.fetch_all(
        "SELECT stored_path FROM attachments WHERE workspace_id = ?",
        (workspace_id,),
    )
    await db.execute("DELETE FROM workspaces WHERE id = ?", (workspace_id,))
    await blobs.delete_many([object_key(workspace_id, row["stored_path"]) for row in attachments])
    return True


async def list_projects(db, workspace_id: int) -> list[dict]:
    return await db.fetch_all(
        PROJECT_SELECT + " WHERE p.workspace_id = ? ORDER BY p.id",
        (workspace_id,),
    )


async def get_project(db, workspace_id: int, project_id: int) -> dict | None:
    return await db.fetch_one(
        PROJECT_SELECT + " WHERE p.workspace_id = ? AND p.id = ?",
        (workspace_id, project_id),
    )


async def create_project(db, workspace_id: int, data: dict) -> dict:
    now = utcnow()
    created = await db.fetch_one(
        """
        INSERT INTO projects (
          workspace_id, name, color, description, start_date, end_date, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)
        RETURNING id
        """,
        (
            workspace_id,
            data["name"],
            data.get("color") or "#0071e3",
            data.get("description"),
            data.get("start_date"),
            data.get("end_date"),
            now,
            now,
        ),
    )
    return await get_project(db, workspace_id, created["id"])


async def update_project(db, workspace_id: int, project_id: int, data: dict) -> dict | None:
    if await get_project(db, workspace_id, project_id) is None:
        return None
    values = {
        key: data[key]
        for key in ("name", "color", "description", "start_date", "end_date", "status")
        if key in data
    }
    if values:
        values["updated_at"] = utcnow()
        await _update(db, "projects", values, "id = ? AND workspace_id = ?", (project_id, workspace_id))
    return await get_project(db, workspace_id, project_id)


async def delete_project(db, blobs, workspace_id: int, project_id: int) -> bool:
    if await get_project(db, workspace_id, project_id) is None:
        return False
    task_ids = [
        row["id"]
        for row in await db.fetch_all(
            "SELECT id FROM tasks WHERE workspace_id = ? AND project_id = ?",
            (workspace_id, project_id),
        )
    ]
    cost_ids = [
        row["id"]
        for row in await db.fetch_all(
            "SELECT id FROM costs WHERE workspace_id = ? AND project_id = ?",
            (workspace_id, project_id),
        )
    ]
    await delete_entity_attachments(db, blobs, workspace_id, "task", task_ids)
    await delete_entity_attachments(db, blobs, workspace_id, "cost", cost_ids)
    await db.execute(
        "DELETE FROM projects WHERE id = ? AND workspace_id = ?",
        (project_id, workspace_id),
    )
    return True


async def _validate_parent(db, workspace_id: int, project_id: int, parent_id: int | None, task_id: int | None = None) -> None:
    if parent_id is None:
        return
    parent = await get_task(db, workspace_id, parent_id)
    if parent is None:
        raise Conflict("parent not found")
    if parent["project_id"] != project_id:
        raise Conflict("parent belongs to different project")
    if task_id is not None and parent_id == task_id:
        raise Conflict("task cannot be its own parent")
    if task_id is None:
        return
    cursor = parent_id
    seen: set[int] = set()
    while cursor is not None:
        if cursor == task_id:
            raise Conflict("would create cycle")
        if cursor in seen:
            break
        seen.add(cursor)
        node = await get_task(db, workspace_id, cursor)
        if node is None:
            break
        cursor = node["parent_id"]


async def list_tasks(db, workspace_id: int, project_id: int) -> list[dict]:
    rows = await db.fetch_all(
        f"""
        SELECT {TASK_PUBLIC} FROM tasks
        WHERE workspace_id = ? AND project_id = ?
        ORDER BY sort_order, id
        """,
        (workspace_id, project_id),
    )
    return flag_all(rows, "is_milestone")


async def get_task(db, workspace_id: int, task_id: int) -> dict | None:
    row = await db.fetch_one(
        f"SELECT {TASK_PUBLIC} FROM tasks WHERE workspace_id = ? AND id = ?",
        (workspace_id, task_id),
    )
    return flag(row, "is_milestone")


async def create_task(db, workspace_id: int, project_id: int, data: dict) -> dict:
    if await get_project(db, workspace_id, project_id) is None:
        raise LookupError("Project not found")
    await _validate_parent(db, workspace_id, project_id, data.get("parent_id"))
    now = utcnow()
    created = await db.fetch_one(
        f"""
        INSERT INTO tasks (
          workspace_id, project_id, parent_id, name, description, status, priority,
          start_date, end_date, progress, sort_order, is_milestone, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING {TASK_PUBLIC}
        """,
        (
            workspace_id,
            project_id,
            data.get("parent_id"),
            data["name"],
            data.get("description"),
            data.get("status") or "todo",
            data.get("priority") or "normal",
            data.get("start_date"),
            data.get("end_date"),
            0 if data.get("progress") is None else data.get("progress"),
            0 if data.get("sort_order") is None else data.get("sort_order"),
            bool(data.get("is_milestone")),
            now,
            now,
        ),
    )
    return flag(created, "is_milestone")


async def update_task(db, workspace_id: int, task_id: int, data: dict) -> dict | None:
    current = await get_task(db, workspace_id, task_id)
    if current is None:
        return None
    allowed = (
        "name", "description", "parent_id", "status", "priority",
        "start_date", "end_date", "progress", "is_milestone", "sort_order",
    )
    values = {key: data[key] for key in allowed if key in data}
    if "parent_id" in values:
        await _validate_parent(db, workspace_id, current["project_id"], values["parent_id"], task_id)
    if "is_milestone" in values:
        values["is_milestone"] = bool(values["is_milestone"])
    if values:
        values["updated_at"] = utcnow()
        await _update(db, "tasks", values, "id = ? AND workspace_id = ?", (task_id, workspace_id))
    return await get_task(db, workspace_id, task_id)


async def move_task(db, workspace_id: int, task_id: int, start_date, end_date) -> dict | None:
    if await get_task(db, workspace_id, task_id) is None:
        return None
    await db.execute(
        """
        UPDATE tasks SET start_date = ?, end_date = ?, updated_at = ?
        WHERE id = ? AND workspace_id = ?
        """,
        (start_date, end_date, utcnow(), task_id, workspace_id),
    )
    return await get_task(db, workspace_id, task_id)


async def delete_task(db, blobs, workspace_id: int, task_id: int) -> bool:
    if await get_task(db, workspace_id, task_id) is None:
        return False
    rows = await db.fetch_all(
        """
        WITH RECURSIVE sub(id) AS (
          SELECT id FROM tasks WHERE workspace_id = ? AND id = ?
          UNION ALL
          SELECT t.id FROM tasks t
          JOIN sub ON t.parent_id = sub.id
          WHERE t.workspace_id = ?
        )
        SELECT id FROM sub
        """,
        (workspace_id, task_id, workspace_id),
    )
    await delete_entity_attachments(db, blobs, workspace_id, "task", [row["id"] for row in rows])
    await db.execute(
        "DELETE FROM tasks WHERE id = ? AND workspace_id = ?",
        (task_id, workspace_id),
    )
    return True


async def list_dependencies(db, workspace_id: int, project_id: int) -> list[dict]:
    return await db.fetch_all(
        f"""
        SELECT d.id, d.predecessor_id, d.successor_id, d.dep_type, d.created_at
        FROM task_dependencies d
        JOIN tasks t ON t.id = d.successor_id
        WHERE d.workspace_id = ? AND t.project_id = ? AND t.workspace_id = ?
        ORDER BY d.id
        """,
        (workspace_id, project_id, workspace_id),
    )


async def _dependency_cycle(db, workspace_id: int, predecessor_id: int, successor_id: int) -> bool:
    rows = await db.fetch_all(
        "SELECT predecessor_id, successor_id FROM task_dependencies WHERE workspace_id = ?",
        (workspace_id,),
    )
    downstream: dict[int, list[int]] = {}
    for row in rows:
        downstream.setdefault(row["predecessor_id"], []).append(row["successor_id"])
    seen: set[int] = set()
    stack = [successor_id]
    while stack:
        node = stack.pop()
        if node == predecessor_id:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(downstream.get(node, []))
    return False


async def add_dependency(db, workspace_id: int, successor_id: int, predecessor_id: int, dep_type: str) -> tuple[dict, bool]:
    successor = await get_task(db, workspace_id, successor_id)
    predecessor = await get_task(db, workspace_id, predecessor_id)
    if successor is None or predecessor is None:
        raise LookupError("Task not found")
    if successor["id"] == predecessor["id"]:
        raise ValueError("Self-dependency not allowed")
    if successor["project_id"] != predecessor["project_id"]:
        raise ValueError("Dependency must be within the same project")
    existing = await db.fetch_one(
        f"""
        SELECT {DEP_PUBLIC} FROM task_dependencies
        WHERE workspace_id = ? AND predecessor_id = ? AND successor_id = ?
        """,
        (workspace_id, predecessor_id, successor_id),
    )
    if existing:
        return existing, False
    if await _dependency_cycle(db, workspace_id, predecessor_id, successor_id):
        raise ValueError("Dependency would create cycle")
    created = await db.fetch_one(
        f"""
        INSERT INTO task_dependencies (
          workspace_id, predecessor_id, successor_id, dep_type, created_at
        ) VALUES (?, ?, ?, ?, ?)
        RETURNING {DEP_PUBLIC}
        """,
        (workspace_id, predecessor_id, successor_id, dep_type, utcnow()),
    )
    return created, True


async def delete_dependency(db, workspace_id: int, dependency_id: int) -> bool:
    _, changes = await db.execute(
        "DELETE FROM task_dependencies WHERE id = ? AND workspace_id = ?",
        (dependency_id, workspace_id),
    )
    return changes > 0


async def _require_task_in_project(db, workspace_id: int, project_id: int, task_id: int | None) -> None:
    if task_id is None:
        return
    task = await get_task(db, workspace_id, task_id)
    if task is None:
        raise ValueError("任务不存在")
    if task["project_id"] != project_id:
        raise ValueError("任务不属于该项目")


async def list_costs(db, workspace_id: int, project_id: int) -> list[dict]:
    return await db.fetch_all(
        f"""
        SELECT {COST_PUBLIC} FROM costs
        WHERE workspace_id = ? AND project_id = ?
        ORDER BY spent_at DESC, id DESC
        """,
        (workspace_id, project_id),
    )


async def get_cost(db, workspace_id: int, cost_id: int) -> dict | None:
    return await db.fetch_one(
        f"SELECT {COST_PUBLIC} FROM costs WHERE workspace_id = ? AND id = ?",
        (workspace_id, cost_id),
    )


async def create_cost(db, workspace_id: int, data: dict) -> dict:
    if await get_project(db, workspace_id, data["project_id"]) is None:
        raise LookupError("Project not found")
    await _require_task_in_project(db, workspace_id, data["project_id"], data.get("task_id"))
    created = await db.fetch_one(
        f"""
        INSERT INTO costs (
          workspace_id, project_id, task_id, name, category, amount, description, spent_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING {COST_PUBLIC}
        """,
        (
            workspace_id,
            data["project_id"],
            data.get("task_id"),
            data["name"],
            data.get("category") or "other",
            data["amount"],
            data.get("description"),
            data["spent_at"],
            utcnow(),
        ),
    )
    return created


async def update_cost(db, workspace_id: int, cost_id: int, data: dict) -> dict | None:
    current = await get_cost(db, workspace_id, cost_id)
    if current is None:
        return None
    values = {
        key: data[key]
        for key in ("name", "category", "amount", "description", "spent_at", "task_id", "project_id")
        if key in data
    }
    new_project = values.get("project_id", current["project_id"])
    if "project_id" in values and await get_project(db, workspace_id, new_project) is None:
        raise ValueError("项目不存在")
    if "task_id" in values:
        await _require_task_in_project(db, workspace_id, new_project, values["task_id"])
    elif "project_id" in values and current["task_id"] is not None:
        task = await get_task(db, workspace_id, current["task_id"])
        if task is None or task["project_id"] != new_project:
            values["task_id"] = None
    if values:
        await _update(db, "costs", values, "id = ? AND workspace_id = ?", (cost_id, workspace_id))
    return await get_cost(db, workspace_id, cost_id)


async def delete_cost(db, blobs, workspace_id: int, cost_id: int) -> bool:
    if await get_cost(db, workspace_id, cost_id) is None:
        return False
    await delete_entity_attachments(db, blobs, workspace_id, "cost", [cost_id])
    await db.execute("DELETE FROM costs WHERE id = ? AND workspace_id = ?", (cost_id, workspace_id))
    return True


async def cost_stats(db, workspace_id: int, project_id: int | None) -> dict:
    params: tuple = (workspace_id,)
    where = "workspace_id = ?"
    if project_id is not None:
        if await get_project(db, workspace_id, project_id) is None:
            raise LookupError("Project not found")
        where = "workspace_id = ? AND project_id = ?"
        params = (workspace_id, project_id)
    totals = await db.fetch_one(
        f"SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count FROM costs WHERE {where}",
        params,
    )
    by_category = await db.fetch_all(
        f"SELECT category, SUM(amount) AS amount FROM costs WHERE {where} GROUP BY category",
        params,
    )
    by_month = await db.fetch_all(
        f"""
        SELECT substr(spent_at, 1, 7) AS month, SUM(amount) AS amount
        FROM costs WHERE {where}
        GROUP BY month
        ORDER BY month
        """,
        params,
    )
    return {
        "total": round(float(totals["total"] or 0), 2),
        "count": int(totals["count"] or 0),
        "by_category": {row["category"]: round(float(row["amount"]), 2) for row in by_category},
        "by_month": {row["month"]: round(float(row["amount"]), 2) for row in by_month if row["month"]},
    }


def _compute_progress(tasks: list[dict]) -> int:
    children: dict[int | None, list[dict]] = {}
    for task in tasks:
        children.setdefault(task["parent_id"], []).append(task)

    def weight(task: dict) -> int:
        subs = children.get(task["id"], [])
        if not subs:
            return 1
        return sum(weight(child) for child in subs)

    def done_weight(task: dict) -> int:
        if task["status"] == "done":
            return weight(task)
        return sum(done_weight(child) for child in children.get(task["id"], []))

    roots = children.get(None, [])
    total = sum(weight(task) for task in roots)
    if total == 0:
        return 0
    done = sum(done_weight(task) for task in roots)
    return round(done / total * 100)


async def overview(db, workspace_id: int) -> dict:
    today = today_local()
    projects = await list_projects(db, workspace_id)
    tasks = await db.fetch_all(
        """
        SELECT id, project_id, parent_id, name, status, end_date
        FROM tasks WHERE workspace_id = ?
        """,
        (workspace_id,),
    )
    month = f"{today.year:04d}-{today.month:02d}"
    cost_row = await db.fetch_one(
        """
        SELECT COALESCE(SUM(amount), 0) AS total FROM costs
        WHERE workspace_id = ? AND substr(spent_at, 1, 7) = ?
        """,
        (workspace_id, month),
    )
    project_rows = []
    for project in projects:
        owned = [task for task in tasks if task["project_id"] == project["id"]]
        due = [
            task for task in owned
            if task["end_date"] and task["end_date"] >= today.isoformat()
            and task["status"] not in ("done", "cancelled")
        ]
        next_due = min(due, key=lambda task: task["end_date"]) if due else None
        project_rows.append({
            "id": project["id"],
            "name": project["name"],
            "color": project["color"],
            "task_total": len(owned),
            "task_done": sum(1 for task in owned if task["status"] == "done"),
            "progress": _compute_progress(owned),
            "next_due_task": {
                "id": next_due["id"],
                "name": next_due["name"],
                "end_date": next_due["end_date"],
            } if next_due else None,
        })
    return {
        "project_count": len(projects),
        "active_task_count": sum(1 for task in tasks if task["status"] == "progress"),
        "delayed_task_count": sum(1 for task in tasks if task["status"] == "delayed"),
        "this_month_cost": round(float(cost_row["total"] or 0), 2),
        "projects": project_rows,
    }


async def list_categories(db, workspace_id: int) -> list[dict]:
    rows = await db.fetch_all(
        f"""
        SELECT {CATEGORY_PUBLIC} FROM cost_categories
        WHERE workspace_id = ?
        ORDER BY sort_order, id
        """,
        (workspace_id,),
    )
    return flag_all(rows, "is_builtin")


async def get_category(db, workspace_id: int, category_id: int) -> dict | None:
    row = await db.fetch_one(
        f"SELECT {CATEGORY_PUBLIC} FROM cost_categories WHERE workspace_id = ? AND id = ?",
        (workspace_id, category_id),
    )
    return flag(row, "is_builtin")


async def create_category(db, workspace_id: int, data: dict) -> dict:
    existing = await db.fetch_one(
        "SELECT id FROM cost_categories WHERE workspace_id = ? AND name = ?",
        (workspace_id, data["name"]),
    )
    if existing:
        raise Conflict("类别名已存在")
    created = await db.fetch_one(
        f"""
        INSERT INTO cost_categories (workspace_id, name, color, is_builtin, sort_order)
        VALUES (?, ?, ?, 0, ?)
        RETURNING {CATEGORY_PUBLIC}
        """,
        (workspace_id, data["name"], data.get("color") or "#8e8e93", data.get("sort_order") or 0),
    )
    return flag(created, "is_builtin")


async def update_category(db, workspace_id: int, category_id: int, data: dict) -> dict | None:
    current = await get_category(db, workspace_id, category_id)
    if current is None:
        return None
    if "name" in data and data["name"] != current["name"]:
        existing = await db.fetch_one(
            "SELECT id FROM cost_categories WHERE workspace_id = ? AND name = ? AND id != ?",
            (workspace_id, data["name"], category_id),
        )
        if existing:
            raise Conflict("类别名已存在")
        await db.execute(
            "UPDATE costs SET category = ? WHERE workspace_id = ? AND category = ?",
            (data["name"], workspace_id, current["name"]),
        )
    values = {key: data[key] for key in ("name", "color", "sort_order") if key in data}
    if values:
        await _update(db, "cost_categories", values, "id = ? AND workspace_id = ?", (category_id, workspace_id))
    return await get_category(db, workspace_id, category_id)


async def delete_category(db, workspace_id: int, category_id: int) -> bool:
    current = await get_category(db, workspace_id, category_id)
    if current is None:
        return False
    used = await db.fetch_one(
        "SELECT COUNT(*) AS n FROM costs WHERE workspace_id = ? AND category = ?",
        (workspace_id, current["name"]),
    )
    if int(used["n"]) > 0:
        raise Conflict(f"该类别已被 {used['n']} 笔费用使用")
    await db.execute(
        "DELETE FROM cost_categories WHERE id = ? AND workspace_id = ?",
        (category_id, workspace_id),
    )
    return True


async def list_inbox(db, workspace_id: int, kind: str | None) -> list[dict]:
    if kind:
        return await db.fetch_all(
            f"""
            SELECT {INBOX_PUBLIC} FROM inbox_items
            WHERE workspace_id = ? AND kind = ?
            ORDER BY created_at DESC, id DESC
            """,
            (workspace_id, kind),
        )
    return await db.fetch_all(
        f"""
        SELECT {INBOX_PUBLIC} FROM inbox_items
        WHERE workspace_id = ?
        ORDER BY created_at DESC, id DESC
        """,
        (workspace_id,),
    )


async def get_inbox(db, workspace_id: int, item_id: int) -> dict | None:
    return await db.fetch_one(
        f"SELECT {INBOX_PUBLIC} FROM inbox_items WHERE workspace_id = ? AND id = ?",
        (workspace_id, item_id),
    )


async def _ensure_optional_project(db, workspace_id: int, project_id: int | None) -> None:
    if project_id is None:
        return
    if await get_project(db, workspace_id, project_id) is None:
        raise ValueError("项目不存在")


async def create_inbox(db, workspace_id: int, data: dict) -> dict:
    await _ensure_optional_project(db, workspace_id, data.get("project_id"))
    priority = data.get("priority") or "normal"
    if priority not in PRIORITIES:
        priority = "normal"
    created = await db.fetch_one(
        f"""
        INSERT INTO inbox_items (
          workspace_id, kind, title, notes, priority, due_at, project_id, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)
        RETURNING {INBOX_PUBLIC}
        """,
        (
            workspace_id,
            data.get("kind") or "idea",
            data["title"],
            data.get("notes"),
            priority,
            data.get("due_at"),
            data.get("project_id"),
            utcnow(),
        ),
    )
    return created


async def update_inbox(db, workspace_id: int, item_id: int, data: dict) -> dict | None:
    current = await get_inbox(db, workspace_id, item_id)
    if current is None:
        return None
    values = {
        key: data[key]
        for key in ("title", "notes", "priority", "due_at", "project_id", "status")
        if key in data
    }
    if "project_id" in values:
        await _ensure_optional_project(db, workspace_id, values["project_id"])
    if "status" in values:
        if values["status"] == "completed" and current["status"] != "completed":
            values["completed_at"] = utcnow()
        elif values["status"] != "completed":
            values["completed_at"] = None
    if values:
        await _update(db, "inbox_items", values, "id = ? AND workspace_id = ?", (item_id, workspace_id))
    return await get_inbox(db, workspace_id, item_id)


async def promote_inbox(db, workspace_id: int, item_id: int, data: dict) -> dict | None:
    item = await get_inbox(db, workspace_id, item_id)
    if item is None:
        return None
    project_id = data.get("project_id") or item["project_id"]
    if project_id is None:
        raise ValueError("project_id is required to promote")
    if await get_project(db, workspace_id, project_id) is None:
        raise ValueError("项目不存在")
    start = date.fromisoformat(data["start_date"]) if data.get("start_date") else today_local()
    end = date.fromisoformat(data["end_date"]) if data.get("end_date") else start + timedelta(days=1)
    name = (data.get("name") or item["title"] or "").strip()[:200]
    if not name:
        raise ValueError("任务名称不能为空")
    priority = item["priority"] if item["priority"] in PRIORITIES else "normal"
    task = await create_task(db, workspace_id, project_id, {
        "name": name,
        "priority": priority,
        "start_date": start,
        "end_date": end,
        "status": "todo",
        "description": None,
        "parent_id": None,
        "progress": 0,
        "is_milestone": False,
        "sort_order": 0,
    })
    await db.execute(
        """
        UPDATE inbox_items SET promoted_task_id = ?, status = 'archived'
        WHERE id = ? AND workspace_id = ?
        """,
        (task["id"], item_id, workspace_id),
    )
    return await get_inbox(db, workspace_id, item_id)


async def delete_inbox(db, blobs, workspace_id: int, item_id: int) -> bool:
    if await get_inbox(db, workspace_id, item_id) is None:
        return False
    await delete_entity_attachments(db, blobs, workspace_id, "inbox", [item_id])
    await db.execute(
        "DELETE FROM inbox_items WHERE id = ? AND workspace_id = ?",
        (item_id, workspace_id),
    )
    return True


def _safe_extension(filename: str) -> str:
    name = Path(filename or "").name
    if "." not in name:
        return ""
    ext = name.rsplit(".", 1)[-1].lower()
    if not ext or len(ext) > 10 or not ext.replace("_", "").isalnum():
        return ""
    return ext


async def entity_exists(db, workspace_id: int, entity_type: str, entity_id: int) -> bool:
    table = ENTITY_TABLES.get(entity_type)
    if table is None:
        return False
    row = await db.fetch_one(
        f"SELECT id FROM {table} WHERE id = ? AND workspace_id = ?",
        (entity_id, workspace_id),
    )
    return row is not None


async def list_attachments(db, workspace_id: int, entity_type: str, entity_id: int) -> list[dict]:
    if entity_type not in ENTITY_LIMITS:
        raise ValueError(f"不支持的实体类型: {entity_type}")
    return await db.fetch_all(
        f"""
        SELECT {ATT_PUBLIC} FROM attachments
        WHERE workspace_id = ? AND entity_type = ? AND entity_id = ?
        ORDER BY uploaded_at DESC, id DESC
        """,
        (workspace_id, entity_type, entity_id),
    )


async def get_attachment(db, workspace_id: int, attachment_id: int) -> dict | None:
    return await db.fetch_one(
        f"""
        SELECT {ATT_PUBLIC}, stored_path FROM attachments
        WHERE workspace_id = ? AND id = ?
        """,
        (workspace_id, attachment_id),
    )


async def save_attachment(
    db,
    blobs,
    workspace_id: int,
    entity_type: str,
    entity_id: int,
    filename: str,
    content_type: str | None,
    content: bytes,
) -> dict:
    if entity_type not in ENTITY_LIMITS:
        raise ValueError(f"不支持的实体类型: {entity_type}")
    if not await entity_exists(db, workspace_id, entity_type, entity_id):
        raise LookupError(f"{entity_type} #{entity_id} 不存在")
    if len(content) > MAX_FILE_BYTES:
        raise PayloadTooLarge(f"文件超过 {MAX_FILE_BYTES // (1024 * 1024)} MB 限制")
    count_row = await db.fetch_one(
        """
        SELECT COUNT(*) AS n FROM attachments
        WHERE workspace_id = ? AND entity_type = ? AND entity_id = ?
        """,
        (workspace_id, entity_type, entity_id),
    )
    if int(count_row["n"]) >= ENTITY_LIMITS[entity_type]:
        raise ValueError(f"{entity_type} 附件已达上限 ({ENTITY_LIMITS[entity_type]} 个)")
    ext = _safe_extension(filename)
    stored_name = secrets.token_hex(16) + (f".{ext}" if ext else "")
    stored_path = f"attachments/{entity_type}/{entity_id}/{stored_name}"
    original = Path(filename or stored_name).name[:255] or stored_name
    mime = (content_type or "application/octet-stream")[:100]
    await blobs.put(object_key(workspace_id, stored_path), content, mime)
    created = await db.fetch_one(
        f"""
        INSERT INTO attachments (
          workspace_id, entity_type, entity_id, original_name, mime, size, stored_path, uploaded_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING {ATT_PUBLIC}
        """,
        (workspace_id, entity_type, entity_id, original, mime, len(content), stored_path, utcnow()),
    )
    return created


async def delete_attachment(db, blobs, workspace_id: int, attachment_id: int) -> bool:
    row = await get_attachment(db, workspace_id, attachment_id)
    if row is None:
        return False
    await blobs.delete_many([object_key(workspace_id, row["stored_path"])])
    await db.execute(
        "DELETE FROM attachments WHERE id = ? AND workspace_id = ?",
        (attachment_id, workspace_id),
    )
    return True


async def delete_entity_attachments(db, blobs, workspace_id: int, entity_type: str, entity_ids: list[int]) -> None:
    if entity_type not in ENTITY_LIMITS or not entity_ids:
        return
    paths: list[str] = []
    for chunk_ids in chunks(list(entity_ids), 100):
        marks = ",".join("?" * len(chunk_ids))
        rows = await db.fetch_all(
            f"""
            SELECT stored_path FROM attachments
            WHERE workspace_id = ? AND entity_type = ? AND entity_id IN ({marks})
            """,
            (workspace_id, entity_type, *chunk_ids),
        )
        paths.extend(row["stored_path"] for row in rows)
        await db.execute(
            f"""
            DELETE FROM attachments
            WHERE workspace_id = ? AND entity_type = ? AND entity_id IN ({marks})
            """,
            (workspace_id, entity_type, *chunk_ids),
        )
    await blobs.delete_many([object_key(workspace_id, path) for path in paths])
