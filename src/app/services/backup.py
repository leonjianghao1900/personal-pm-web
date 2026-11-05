"""Workspace ZIP/JSON backup.

The JSON body stays compatible with personal-pm export versions 1–3 so a
desktop backup can be restored into one workspace. Ids are remapped on
restore so two workspaces never collide in the shared D1 database. Restore
replaces only the current workspace's rows and R2 objects.
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import date, datetime, timezone

from app.blobs import object_key

EXPORT_VERSION = 3
SUPPORTED_VERSIONS = {1, 2, 3}
MAX_JSON_BYTES = 50 * 1024 * 1024
MAX_ZIP_BYTES = 100 * 1024 * 1024
MAX_UNCOMPRESSED = 120 * 1024 * 1024

TABLES = (
    "projects",
    "tasks",
    "task_dependencies",
    "costs",
    "cost_categories",
    "inbox_items",
    "attachments",
)


def _require_list(payload: dict, key: str) -> list:
    if key not in payload:
        raise ValueError(f"备份缺少数据表: {key}")
    rows = payload[key]
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"备份表 {key} 必须是对象数组")
    return rows


def _as_int(value, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        if isinstance(value, float) and value.is_integer():
            return int(value)
        raise ValueError(f"{label} 必须是整数")
    return value


def _as_optional_int(value, label: str) -> int | None:
    if value is None or value == "":
        return None
    return _as_int(value, label)


def _as_text(value, label: str, limit: int, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise ValueError(f"{label} 不能为空")
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} 必须是字符串")
    if required:
        value = value.strip()
        if not value:
            raise ValueError(f"{label} 不能为空")
    if len(value) > limit:
        raise ValueError(f"{label} 过长")
    return value


def _as_date(value, label: str) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} 无效")
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError as exc:
        raise ValueError(f"{label} 无效") from exc


def _as_datetime(value, label: str) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} 无效")
    raw = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{label} 无效") from exc
    text = value[:-1] if value.endswith("Z") else value
    if "+" in text[10:]:
        text = text.split("+", 1)[0]
    return text[:19]


def _as_bit(value, label: str, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if value in (0, 1):
        return int(value)
    raise ValueError(f"{label} 无效")


def _as_amount(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("金额无效")
    if value <= 0:
        raise ValueError("金额必须大于 0")
    return float(value)


def _clean_stored_path(path: str) -> str:
    if not isinstance(path, str):
        raise ValueError("附件路径无效")
    path = path.replace("\\", "/").lstrip("/")
    if path.startswith("ws/"):
        parts = path.split("/", 2)
        if len(parts) == 3 and parts[1].isdigit():
            path = parts[2]
    pieces = path.split("/")
    if not path.startswith("attachments/") or ".." in pieces or "" in pieces:
        raise ValueError("附件路径无效")
    return path


def _unique_ids(rows: list[dict], table: str) -> None:
    seen = set()
    for index, row in enumerate(rows, start=1):
        if row["id"] in seen:
            raise ValueError(f"备份表 {table} 第 {index} 条记录 id 重复")
        seen.add(row["id"])


def _v1_cost_name(cost: dict, index: int) -> str:
    candidates = (cost.get("description"), cost.get("category"))
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()[:200]
    raise ValueError(f"备份表 costs 第 {index} 条记录无法生成名称")


def normalize(payload: dict) -> dict[str, list[dict]]:
    if not isinstance(payload, dict):
        raise ValueError("备份文件不是有效的 JSON 对象")
    version = payload.get("version")
    if type(version) is not int or version not in SUPPORTED_VERSIONS:
        raise ValueError(f"备份版本不支持（支持 1、2、3，得到 {version}）")
    required = ["projects", "tasks", "task_dependencies", "costs", "cost_categories", "inbox_items"]
    if version >= 3:
        required.append("attachments")
    for key in required:
        _require_list(payload, key)

    projects = []
    for index, row in enumerate(payload["projects"], start=1):
        projects.append({
            "id": _as_int(row.get("id"), f"projects[{index}].id"),
            "name": _as_text(row.get("name"), f"projects[{index}].name", 100, required=True),
            "color": _as_text(row.get("color") or "#0071e3", f"projects[{index}].color", 20) or "#0071e3",
            "description": _as_text(row.get("description"), f"projects[{index}].description", 2000),
            "start_date": _as_date(row.get("start_date"), f"projects[{index}].start_date"),
            "end_date": _as_date(row.get("end_date"), f"projects[{index}].end_date"),
            "status": row.get("status") if row.get("status") in ("active", "archived") else "active",
            "created_at": _as_datetime(row.get("created_at"), f"projects[{index}].created_at") or _now(),
            "updated_at": _as_datetime(row.get("updated_at"), f"projects[{index}].updated_at") or _now(),
        })
    _unique_ids(projects, "projects")
    project_ids = {row["id"] for row in projects}

    tasks = []
    for index, row in enumerate(payload["tasks"], start=1):
        project_id = _as_int(row.get("project_id"), f"tasks[{index}].project_id")
        if project_id not in project_ids:
            raise ValueError(f"备份表 tasks 第 {index} 条记录的项目不存在")
        status = row.get("status") if row.get("status") in ("todo", "progress", "delayed", "done", "cancelled") else "todo"
        priority = row.get("priority") if row.get("priority") in ("low", "normal", "high", "urgent") else "normal"
        tasks.append({
            "id": _as_int(row.get("id"), f"tasks[{index}].id"),
            "project_id": project_id,
            "parent_id": _as_optional_int(row.get("parent_id"), f"tasks[{index}].parent_id"),
            "name": _as_text(row.get("name"), f"tasks[{index}].name", 200, required=True),
            "description": _as_text(row.get("description"), f"tasks[{index}].description", 20000),
            "status": status,
            "priority": priority,
            "start_date": _as_date(row.get("start_date"), f"tasks[{index}].start_date"),
            "end_date": _as_date(row.get("end_date"), f"tasks[{index}].end_date"),
            "progress": _as_int(row.get("progress") or 0, f"tasks[{index}].progress"),
            "sort_order": _as_int(row.get("sort_order") or 0, f"tasks[{index}].sort_order"),
            "is_milestone": _as_bit(row.get("is_milestone"), f"tasks[{index}].is_milestone"),
            "created_at": _as_datetime(row.get("created_at"), f"tasks[{index}].created_at") or _now(),
            "updated_at": _as_datetime(row.get("updated_at"), f"tasks[{index}].updated_at") or _now(),
        })
        if not 0 <= tasks[-1]["progress"] <= 100:
            raise ValueError(f"备份表 tasks 第 {index} 条记录进度无效")
    _unique_ids(tasks, "tasks")
    task_ids = {row["id"] for row in tasks}
    task_project = {row["id"]: row["project_id"] for row in tasks}
    for index, task in enumerate(tasks, start=1):
        parent_id = task["parent_id"]
        if parent_id is None:
            continue
        if parent_id not in task_ids:
            raise ValueError(f"备份表 tasks 第 {index} 条记录的父任务不存在")
        if task_project[parent_id] != task["project_id"]:
            raise ValueError(f"备份表 tasks 第 {index} 条记录的父任务不属于同一项目")
        if parent_id == task["id"]:
            raise ValueError(f"备份表 tasks 第 {index} 条记录不能以自己为父任务")
    _assert_parent_acyclic(tasks)

    dependencies = []
    seen_pairs: set[tuple[int, int]] = set()
    for index, row in enumerate(payload["task_dependencies"], start=1):
        predecessor = _as_int(row.get("predecessor_id"), f"deps[{index}].predecessor_id")
        successor = _as_int(row.get("successor_id"), f"deps[{index}].successor_id")
        pair = (predecessor, successor)
        if pair in seen_pairs:
            raise ValueError(f"备份表 task_dependencies 第 {index} 条记录与已有依赖重复")
        seen_pairs.add(pair)
        if predecessor not in task_ids or successor not in task_ids:
            raise ValueError(f"备份表 task_dependencies 第 {index} 条记录引用了不存在的任务")
        if predecessor == successor:
            raise ValueError(f"备份表 task_dependencies 第 {index} 条记录不能依赖自己")
        if task_project[predecessor] != task_project[successor]:
            raise ValueError(f"备份表 task_dependencies 第 {index} 条记录必须属于同一项目")
        dep_type = row.get("dep_type") if row.get("dep_type") in ("FS", "SS", "FF", "SF") else "FS"
        dependencies.append({
            "id": _as_int(row.get("id"), f"deps[{index}].id"),
            "predecessor_id": predecessor,
            "successor_id": successor,
            "dep_type": dep_type,
            "created_at": _as_datetime(row.get("created_at"), f"deps[{index}].created_at") or _now(),
        })
    _unique_ids(dependencies, "task_dependencies")
    _assert_dependency_acyclic(dependencies)

    categories = []
    seen_names = set()
    for index, row in enumerate(payload["cost_categories"], start=1):
        name = _as_text(row.get("name"), f"categories[{index}].name", 50, required=True)
        if name in seen_names:
            raise ValueError(f"备份表 cost_categories 类别名重复: {name}")
        seen_names.add(name)
        categories.append({
            "id": _as_int(row.get("id"), f"categories[{index}].id"),
            "name": name,
            "color": _as_text(row.get("color") or "#8e8e93", f"categories[{index}].color", 20) or "#8e8e93",
            "is_builtin": _as_bit(row.get("is_builtin"), f"categories[{index}].is_builtin"),
            "sort_order": _as_int(row.get("sort_order") or 0, f"categories[{index}].sort_order"),
        })
    _unique_ids(categories, "cost_categories")

    costs = []
    for index, row in enumerate(payload["costs"], start=1):
        if version == 1 and not (isinstance(row.get("name"), str) and row.get("name").strip()):
            name = _v1_cost_name(row, index)
        else:
            name = _as_text(row.get("name"), f"costs[{index}].name", 200, required=True)
        project_id = _as_int(row.get("project_id"), f"costs[{index}].project_id")
        if project_id not in project_ids:
            raise ValueError(f"备份表 costs 第 {index} 条记录的项目不存在")
        task_id = _as_optional_int(row.get("task_id"), f"costs[{index}].task_id")
        if task_id is not None and task_project.get(task_id) != project_id:
            raise ValueError(f"备份表 costs 第 {index} 条记录的任务不属于该项目")
        costs.append({
            "id": _as_int(row.get("id"), f"costs[{index}].id"),
            "project_id": project_id,
            "task_id": task_id,
            "name": name,
            "category": _as_text(row.get("category") or "other", f"costs[{index}].category", 50) or "other",
            "amount": _as_amount(row.get("amount")),
            "description": _as_text(row.get("description"), f"costs[{index}].description", 20000),
            "spent_at": _as_date(row.get("spent_at"), f"costs[{index}].spent_at"),
            "created_at": _as_datetime(row.get("created_at"), f"costs[{index}].created_at") or _now(),
        })
        if costs[-1]["spent_at"] is None:
            raise ValueError(f"备份表 costs 第 {index} 条记录缺少支出日期")
    _unique_ids(costs, "costs")

    inbox = []
    for index, row in enumerate(payload["inbox_items"], start=1):
        project_id = _as_optional_int(row.get("project_id"), f"inbox[{index}].project_id")
        if project_id is not None and project_id not in project_ids:
            raise ValueError(f"备份表 inbox_items 第 {index} 条记录的项目不存在")
        promoted = _as_optional_int(row.get("promoted_task_id"), f"inbox[{index}].promoted_task_id")
        if promoted is not None and promoted not in task_ids:
            raise ValueError(f"备份表 inbox_items 第 {index} 条记录的任务不存在")
        kind = row.get("kind") if row.get("kind") in ("interrupt", "idea") else "idea"
        status = row.get("status") if row.get("status") in ("active", "completed", "archived") else "active"
        priority = row.get("priority") if row.get("priority") in ("low", "normal", "high", "urgent") else "normal"
        inbox.append({
            "id": _as_int(row.get("id"), f"inbox[{index}].id"),
            "kind": kind,
            "title": _as_text(row.get("title"), f"inbox[{index}].title", 200, required=True),
            "notes": _as_text(row.get("notes"), f"inbox[{index}].notes", 20000),
            "priority": priority,
            "due_at": _as_datetime(row.get("due_at"), f"inbox[{index}].due_at"),
            "project_id": project_id,
            "promoted_task_id": promoted,
            "status": status,
            "created_at": _as_datetime(row.get("created_at"), f"inbox[{index}].created_at") or _now(),
            "completed_at": _as_datetime(row.get("completed_at"), f"inbox[{index}].completed_at"),
        })
    _unique_ids(inbox, "inbox_items")

    raw_attachments = payload.get("attachments") or []
    if not isinstance(raw_attachments, list):
        raise ValueError("备份表 attachments 必须是对象数组")
    attachments = []
    seen_paths = set()
    for index, row in enumerate(raw_attachments, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"备份表 attachments 第 {index} 条记录无效")
        entity_type = row.get("entity_type")
        if entity_type not in ("task", "cost", "inbox"):
            raise ValueError(f"备份表 attachments 第 {index} 条记录实体类型无效")
        entity_id = _as_int(row.get("entity_id"), f"attachments[{index}].entity_id")
        if entity_type == "task" and entity_id not in task_ids:
            raise ValueError(f"备份表 attachments 第 {index} 条记录的任务不存在")
        if entity_type == "cost" and entity_id not in {item["id"] for item in costs}:
            raise ValueError(f"备份表 attachments 第 {index} 条记录的费用不存在")
        if entity_type == "inbox" and entity_id not in {item["id"] for item in inbox}:
            raise ValueError(f"备份表 attachments 第 {index} 条记录的收件箱条目不存在")
        stored = _clean_stored_path(row.get("stored_path"))
        if stored in seen_paths:
            raise ValueError(f"备份表 attachments 路径重复: {stored}")
        seen_paths.add(stored)
        attachments.append({
            "id": _as_int(row.get("id"), f"attachments[{index}].id"),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "original_name": _as_text(row.get("original_name"), f"attachments[{index}].original_name", 255, required=True),
            "mime": _as_text(row.get("mime") or "application/octet-stream", f"attachments[{index}].mime", 100) or "application/octet-stream",
            "size": _as_int(row.get("size"), f"attachments[{index}].size"),
            "stored_path": stored,
            "uploaded_at": _as_datetime(row.get("uploaded_at"), f"attachments[{index}].uploaded_at") or _now(),
        })
        if attachments[-1]["size"] < 0:
            raise ValueError(f"备份表 attachments 第 {index} 条记录大小无效")
    _unique_ids(attachments, "attachments")

    return {
        "projects": projects,
        "tasks": tasks,
        "task_dependencies": dependencies,
        "costs": costs,
        "cost_categories": categories,
        "inbox_items": inbox,
        "attachments": attachments,
    }


def _assert_parent_acyclic(tasks: list[dict]) -> None:
    parent = {task["id"]: task["parent_id"] for task in tasks}
    for start in parent:
        seen = set()
        cursor = start
        while cursor is not None:
            if cursor in seen:
                raise ValueError("备份中的任务父子关系存在循环")
            seen.add(cursor)
            cursor = parent.get(cursor)


def _assert_dependency_acyclic(dependencies: list[dict]) -> None:
    downstream: dict[int, list[int]] = {}
    for dep in dependencies:
        downstream.setdefault(dep["predecessor_id"], []).append(dep["successor_id"])

    def reaches(start: int, target: int) -> bool:
        seen = set()
        stack = [start]
        while stack:
            node = stack.pop()
            if node == target:
                return True
            if node in seen:
                continue
            seen.add(node)
            stack.extend(downstream.get(node, []))
        return False

    for dep in dependencies:
        if reaches(dep["successor_id"], dep["predecessor_id"]):
            raise ValueError("备份中的任务依赖存在循环")


def _leaf_first(tasks: list[dict]) -> list[int]:
    children: dict[int, list[int]] = {}
    ids: list[int] = []
    for task in tasks:
        ids.append(task["id"])
        if task["parent_id"]:
            children.setdefault(task["parent_id"], []).append(task["id"])
    ordered: list[int] = []
    seen: set[int] = set()

    def walk(task_id: int) -> None:
        for child in children.get(task_id, []):
            walk(child)
        if task_id not in seen:
            seen.add(task_id)
            ordered.append(task_id)

    for task_id in ids:
        walk(task_id)
    return ordered


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")


async def _allocate(db, table: str, old_ids: list[int]) -> dict[int, int]:
    if table not in TABLES:
        raise RuntimeError(table)
    row = await db.fetch_one(f"SELECT COALESCE(MAX(id), 0) AS m FROM {table}")
    nxt = int(row["m"])
    mapping = {}
    for old in old_ids:
        nxt += 1
        mapping[old] = nxt
    return mapping


def _remap(value: int | None, mapping: dict[int, int]) -> int | None:
    if value is None:
        return None
    return mapping[value]


async def export_payload(db, workspace_id: int) -> dict:
    workspace = await db.fetch_one("SELECT name FROM workspaces WHERE id = ?", (workspace_id,))
    projects = await db.fetch_all(
        """
        SELECT id, name, color, description, start_date, end_date, status, created_at, updated_at
        FROM projects WHERE workspace_id = ? ORDER BY id
        """,
        (workspace_id,),
    )
    tasks = await db.fetch_all(
        """
        SELECT id, project_id, parent_id, name, description, status, priority,
               start_date, end_date, progress, sort_order, is_milestone, created_at, updated_at
        FROM tasks WHERE workspace_id = ? ORDER BY id
        """,
        (workspace_id,),
    )
    dependencies = await db.fetch_all(
        """
        SELECT id, predecessor_id, successor_id, dep_type, created_at
        FROM task_dependencies WHERE workspace_id = ? ORDER BY id
        """,
        (workspace_id,),
    )
    costs = await db.fetch_all(
        """
        SELECT id, project_id, task_id, name, category, amount, description, spent_at, created_at
        FROM costs WHERE workspace_id = ? ORDER BY id
        """,
        (workspace_id,),
    )
    categories = await db.fetch_all(
        """
        SELECT id, name, color, is_builtin, sort_order
        FROM cost_categories WHERE workspace_id = ? ORDER BY id
        """,
        (workspace_id,),
    )
    inbox = await db.fetch_all(
        """
        SELECT id, kind, title, notes, priority, due_at, project_id, promoted_task_id,
               status, created_at, completed_at
        FROM inbox_items WHERE workspace_id = ? ORDER BY id
        """,
        (workspace_id,),
    )
    attachments = await db.fetch_all(
        """
        SELECT id, entity_type, entity_id, original_name, mime, size, stored_path, uploaded_at
        FROM attachments WHERE workspace_id = ? ORDER BY id
        """,
        (workspace_id,),
    )
    return {
        "version": EXPORT_VERSION,
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workspace_name": workspace["name"] if workspace else "",
        "projects": projects,
        "tasks": tasks,
        "task_dependencies": dependencies,
        "costs": costs,
        "cost_categories": categories,
        "inbox_items": inbox,
        "attachments": attachments,
    }


async def export_full(db, blobs, workspace_id: int) -> tuple[bytes, str]:
    payload = await export_payload(db, workspace_id)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("backup.json", json.dumps(payload, ensure_ascii=False, indent=2))
        for attachment in payload["attachments"]:
            data = await blobs.get(object_key(workspace_id, attachment["stored_path"]))
            if data is None:
                continue
            archive.writestr(attachment["stored_path"], data)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return buffer.getvalue(), f"pm-backup-full-{stamp}.zip"


def read_zip(raw: bytes) -> tuple[dict, dict[str, bytes]]:
    if len(raw) > MAX_ZIP_BYTES:
        raise ValueError("备份 zip 超过 100MB 限制")
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise ValueError("不是有效的 zip 文件") from exc
    total = 0
    files: dict[str, bytes] = {}
    with archive:
        try:
            payload_bytes = archive.read("backup.json")
        except KeyError as exc:
            raise ValueError("备份 zip 缺少 backup.json") from exc
        if len(payload_bytes) > MAX_JSON_BYTES:
            raise ValueError("backup.json 超过 50MB 限制")
        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"JSON 解析失败: {exc}") from exc
        for info in archive.infolist():
            name = info.filename
            if name.endswith("/") or name == "backup.json":
                continue
            if name.startswith("/") or ".." in name.split("/"):
                raise ValueError("备份 zip 包含非法路径")
            total += info.file_size
            if total > MAX_UNCOMPRESSED:
                raise ValueError("备份解压后超过限制")
            files[name] = archive.read(info)
    return payload, files


def lookup_file(files: dict[str, bytes], stored_path: str) -> bytes | None:
    relative = stored_path.removeprefix("attachments/")
    for candidate in (stored_path, f"attachments/{relative}", relative):
        if candidate in files:
            return files[candidate]
    return None


async def restore_workspace(db, blobs, workspace_id: int, payload: dict, files: dict[str, bytes] | None) -> dict[str, int]:
    tables = normalize(payload)
    maps = {
        "projects": await _allocate(db, "projects", [row["id"] for row in tables["projects"]]),
        "tasks": await _allocate(db, "tasks", [row["id"] for row in tables["tasks"]]),
        "task_dependencies": await _allocate(db, "task_dependencies", [row["id"] for row in tables["task_dependencies"]]),
        "costs": await _allocate(db, "costs", [row["id"] for row in tables["costs"]]),
        "cost_categories": await _allocate(db, "cost_categories", [row["id"] for row in tables["cost_categories"]]),
        "inbox_items": await _allocate(db, "inbox_items", [row["id"] for row in tables["inbox_items"]]),
        "attachments": await _allocate(db, "attachments", [row["id"] for row in tables["attachments"]]),
    }
    projects = []
    for row in tables["projects"]:
        item = dict(row)
        item["id"] = maps["projects"][row["id"]]
        projects.append(item)
    tasks = []
    for row in tables["tasks"]:
        item = dict(row)
        item["id"] = maps["tasks"][row["id"]]
        item["project_id"] = maps["projects"][row["project_id"]]
        item["parent_id"] = _remap(row["parent_id"], maps["tasks"])
        tasks.append(item)
    dependencies = []
    for row in tables["task_dependencies"]:
        item = dict(row)
        item["id"] = maps["task_dependencies"][row["id"]]
        item["predecessor_id"] = maps["tasks"][row["predecessor_id"]]
        item["successor_id"] = maps["tasks"][row["successor_id"]]
        dependencies.append(item)
    costs = []
    for row in tables["costs"]:
        item = dict(row)
        item["id"] = maps["costs"][row["id"]]
        item["project_id"] = maps["projects"][row["project_id"]]
        item["task_id"] = _remap(row["task_id"], maps["tasks"])
        costs.append(item)
    categories = []
    for row in tables["cost_categories"]:
        item = dict(row)
        item["id"] = maps["cost_categories"][row["id"]]
        categories.append(item)
    inbox = []
    for row in tables["inbox_items"]:
        item = dict(row)
        item["id"] = maps["inbox_items"][row["id"]]
        item["project_id"] = _remap(row["project_id"], maps["projects"])
        item["promoted_task_id"] = _remap(row["promoted_task_id"], maps["tasks"])
        inbox.append(item)
    entity_maps = {"task": maps["tasks"], "cost": maps["costs"], "inbox": maps["inbox_items"]}
    attachments = []
    for row in tables["attachments"]:
        item = dict(row)
        item["id"] = maps["attachments"][row["id"]]
        item["entity_id"] = entity_maps[row["entity_type"]][row["entity_id"]]
        attachments.append(item)

    old_rows = await db.fetch_all(
        "SELECT stored_path FROM attachments WHERE workspace_id = ?",
        (workspace_id,),
    )
    old_keys = [object_key(workspace_id, row["stored_path"]) for row in old_rows]
    existing_tasks = await db.fetch_all(
        "SELECT id, parent_id FROM tasks WHERE workspace_id = ?",
        (workspace_id,),
    )

    statements: list[tuple[str, tuple]] = [
        ("DELETE FROM attachments WHERE workspace_id = ?", (workspace_id,)),
        ("DELETE FROM inbox_items WHERE workspace_id = ?", (workspace_id,)),
        ("DELETE FROM task_dependencies WHERE workspace_id = ?", (workspace_id,)),
        ("DELETE FROM costs WHERE workspace_id = ?", (workspace_id,)),
    ]
    for task_id in _leaf_first(existing_tasks):
        statements.append(("DELETE FROM tasks WHERE id = ? AND workspace_id = ?", (task_id, workspace_id)))
    statements.extend([
        ("DELETE FROM projects WHERE workspace_id = ?", (workspace_id,)),
        ("DELETE FROM cost_categories WHERE workspace_id = ?", (workspace_id,)),
    ])
    for row in projects:
        statements.append((
            """
            INSERT INTO projects (
              id, workspace_id, name, color, description, start_date, end_date, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"], workspace_id, row["name"], row["color"], row["description"],
                row["start_date"], row["end_date"], row["status"], row["created_at"], row["updated_at"],
            ),
        ))
    for row in categories:
        statements.append((
            """
            INSERT INTO cost_categories (id, workspace_id, name, color, is_builtin, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (row["id"], workspace_id, row["name"], row["color"], row["is_builtin"], row["sort_order"]),
        ))
    for row in tasks:
        statements.append((
            """
            INSERT INTO tasks (
              id, workspace_id, project_id, parent_id, name, description, status, priority,
              start_date, end_date, progress, sort_order, is_milestone, created_at, updated_at
            ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"], workspace_id, row["project_id"], row["name"], row["description"],
                row["status"], row["priority"], row["start_date"], row["end_date"],
                row["progress"], row["sort_order"], row["is_milestone"], row["created_at"], row["updated_at"],
            ),
        ))
    for row in tasks:
        if row["parent_id"] is not None:
            statements.append((
                "UPDATE tasks SET parent_id = ? WHERE id = ? AND workspace_id = ?",
                (row["parent_id"], row["id"], workspace_id),
            ))
    for row in dependencies:
        statements.append((
            """
            INSERT INTO task_dependencies (
              id, workspace_id, predecessor_id, successor_id, dep_type, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"], workspace_id, row["predecessor_id"], row["successor_id"],
                row["dep_type"], row["created_at"],
            ),
        ))
    for row in costs:
        statements.append((
            """
            INSERT INTO costs (
              id, workspace_id, project_id, task_id, name, category, amount, description, spent_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"], workspace_id, row["project_id"], row["task_id"], row["name"],
                row["category"], row["amount"], row["description"], row["spent_at"], row["created_at"],
            ),
        ))
    for row in inbox:
        statements.append((
            """
            INSERT INTO inbox_items (
              id, workspace_id, kind, title, notes, priority, due_at, project_id,
              promoted_task_id, status, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"], workspace_id, row["kind"], row["title"], row["notes"], row["priority"],
                row["due_at"], row["project_id"], row["promoted_task_id"], row["status"],
                row["created_at"], row["completed_at"],
            ),
        ))
    for row in attachments:
        statements.append((
            """
            INSERT INTO attachments (
              id, workspace_id, entity_type, entity_id, original_name, mime, size, stored_path, uploaded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"], workspace_id, row["entity_type"], row["entity_id"], row["original_name"],
                row["mime"], row["size"], row["stored_path"], row["uploaded_at"],
            ),
        ))
    try:
        await db.batch(statements)
    except Exception as exc:
        raise ValueError(f"备份数据无法写入: {exc}") from exc

    new_keys = {object_key(workspace_id, row["stored_path"]) for row in attachments}
    if files is not None:
        for row in attachments:
            content = lookup_file(files, row["stored_path"])
            if content is None:
                continue
            await blobs.put(object_key(workspace_id, row["stored_path"]), content, row["mime"])
    stale = [key for key in old_keys if key not in new_keys]
    await blobs.delete_many(stale)
    return {key: len(tables[key]) for key in TABLES}
