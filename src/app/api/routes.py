"""HTTP routes. Shapes follow the personal-pm Vue client, plus auth and admin."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Path, Request, Response, UploadFile

from app.authutil import make_token, verify_password
from app.deps import admin_user, current_user, workspace_user
from app.errors import Conflict, PayloadTooLarge
from app.schemas import (
    ChangePasswordIn,
    CostCategoryCreate,
    CostCategoryUpdate,
    CostCreate,
    CostUpdate,
    DependencyCreate,
    InboxCreate,
    InboxPromote,
    InboxUpdate,
    LoginIn,
    ProjectCreate,
    ProjectUpdate,
    TaskCreate,
    TaskMove,
    TaskUpdate,
    UserCreate,
    UserUpdate,
    WorkspaceCreate,
    WorkspaceUpdate,
)
from app.services import backup as backup_service
from app.services import excel_export, store

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])
project_router = APIRouter(prefix="/api/projects", tags=["projects"])
task_router = APIRouter(tags=["tasks"])
cost_router = APIRouter(tags=["costs"])
inbox_router = APIRouter(prefix="/api/inbox", tags=["inbox"])
category_router = APIRouter(prefix="/api/cost-categories", tags=["cost-categories"])
attachment_router = APIRouter(prefix="/api/attachments", tags=["attachments"])
stats_router = APIRouter(prefix="/api/stats", tags=["stats"])


def raise_mapped(exc: Exception) -> None:
    if isinstance(exc, LookupError):
        raise HTTPException(404, str(exc)) from exc
    if isinstance(exc, Conflict):
        raise HTTPException(409, str(exc)) from exc
    if isinstance(exc, PayloadTooLarge):
        raise HTTPException(413, str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(400, str(exc)) from exc
    raise exc


def _secure(request: Request) -> bool:
    return request.url.scheme == "https"


def _set_session(response: Response, request: Request, token: str) -> None:
    settings = request.state.settings
    response.set_cookie(
        settings.cookie_name,
        token,
        max_age=settings.token_ttl_seconds,
        httponly=True,
        secure=_secure(request),
        samesite="lax",
        path="/",
    )


def _clear_session(response: Response, request: Request) -> None:
    settings = request.state.settings
    response.delete_cookie(
        settings.cookie_name,
        path="/",
        httponly=True,
        secure=_secure(request),
        samesite="lax",
    )


@auth_router.post("/login")
async def login(data: LoginIn, request: Request, response: Response):
    settings = request.state.settings
    if not settings.jwt_secret or len(settings.jwt_secret) < 16:
        raise HTTPException(500, "JWT_SECRET 未配置")
    row = await store.get_user_by_email(request.state.db, data.email)
    password_hash = row["password_hash"] if row else None
    if row is None or not await verify_password(data.password, password_hash):
        raise HTTPException(401, "邮箱或密码错误")
    token = make_token(row["id"], settings.jwt_secret, settings.token_ttl_seconds)
    _set_session(response, request, token)
    user = await store.get_user(request.state.db, row["id"])
    return {"user": user}


@auth_router.post("/logout")
async def logout(request: Request, response: Response):
    _clear_session(response, request)
    return {"status": "ok"}


@auth_router.get("/me")
async def me(user: dict = Depends(current_user)):
    return user


@auth_router.post("/change-password")
async def change_password(
    data: ChangePasswordIn,
    request: Request,
    user: dict = Depends(current_user),
):
    try:
        await store.change_password(request.state.db, user["id"], data.current_password, data.new_password)
    except ValueError as exc:
        raise_mapped(exc)
    return await store.get_user(request.state.db, user["id"])


@admin_router.get("/users")
async def list_users(request: Request, _: dict = Depends(admin_user)):
    return await store.list_users(request.state.db)


@admin_router.post("/users", status_code=201)
async def create_user(data: UserCreate, request: Request, _: dict = Depends(admin_user)):
    display = (data.display_name or data.email.split("@", 1)[0] or "用户").strip()[:100]
    try:
        return await store.insert_user(
            request.state.db,
            email=data.email,
            password=data.password,
            display_name=display,
            role=data.role,
            workspace_id=data.workspace_id,
        )
    except (Conflict, ValueError) as exc:
        raise_mapped(exc)


@admin_router.patch("/users/{user_id}")
async def update_user(user_id: int, data: UserUpdate, request: Request, _: dict = Depends(admin_user)):
    try:
        updated = await store.update_user(request.state.db, user_id, data.model_dump(exclude_unset=True))
    except (Conflict, ValueError) as exc:
        raise_mapped(exc)
    if updated is None:
        raise HTTPException(404, "用户不存在")
    return updated


@admin_router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int, request: Request, actor: dict = Depends(admin_user)):
    try:
        deleted = await store.delete_user(request.state.db, user_id, actor["id"])
    except Conflict as exc:
        raise_mapped(exc)
    if not deleted:
        raise HTTPException(404, "用户不存在")
    return Response(status_code=204)


@admin_router.get("/workspaces")
async def list_workspaces(request: Request, _: dict = Depends(admin_user)):
    return await store.list_workspaces(request.state.db)


@admin_router.post("/workspaces", status_code=201)
async def create_workspace(data: WorkspaceCreate, request: Request, _: dict = Depends(admin_user)):
    return await store.create_workspace(request.state.db, data.name)


@admin_router.patch("/workspaces/{workspace_id}")
async def update_workspace(workspace_id: int, data: WorkspaceUpdate, request: Request, _: dict = Depends(admin_user)):
    updated = await store.rename_workspace(request.state.db, workspace_id, data.name)
    if updated is None:
        raise HTTPException(404, "工作区不存在")
    return updated


@admin_router.delete("/workspaces/{workspace_id}", status_code=204)
async def delete_workspace(workspace_id: int, request: Request, _: dict = Depends(admin_user)):
    try:
        deleted = await store.delete_workspace(request.state.db, request.state.blobs, workspace_id)
    except Conflict as exc:
        raise_mapped(exc)
    if not deleted:
        raise HTTPException(404, "工作区不存在")
    return Response(status_code=204)


@admin_router.get("/backup")
async def download_backup(request: Request, user: dict = Depends(workspace_user)):
    payload = await backup_service.export_payload(request.state.db, user["workspace_id"])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="pm-backup-{stamp}.json"'},
    )


@admin_router.post("/restore")
async def restore_backup(
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(workspace_user),
):
    raw = await file.read(backup_service.MAX_JSON_BYTES + 1)
    if len(raw) > backup_service.MAX_JSON_BYTES:
        raise HTTPException(413, "备份文件超过 50MB 限制")
    try:
        payload = json.loads(raw.decode("utf-8"))
        counts = await backup_service.restore_workspace(
            request.state.db, request.state.blobs, user["workspace_id"], payload, None
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"status": "ok", "counts": counts}


@admin_router.get("/backup/full")
async def download_full_backup(request: Request, user: dict = Depends(workspace_user)):
    body, filename = await backup_service.export_full(
        request.state.db, request.state.blobs, user["workspace_id"]
    )
    return Response(
        content=body,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@admin_router.post("/restore/full")
async def restore_full_backup(
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(workspace_user),
):
    raw = await file.read(backup_service.MAX_ZIP_BYTES + 1)
    if len(raw) > backup_service.MAX_ZIP_BYTES:
        raise HTTPException(413, "备份 zip 超过 100MB 限制")
    try:
        payload, files = backup_service.read_zip(raw)
        counts = await backup_service.restore_workspace(
            request.state.db, request.state.blobs, user["workspace_id"], payload, files
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"status": "ok", "counts": counts}


@project_router.get("")
async def list_projects(request: Request, user: dict = Depends(workspace_user)):
    return await store.list_projects(request.state.db, user["workspace_id"])


@project_router.post("", status_code=201)
async def create_project(data: ProjectCreate, request: Request, user: dict = Depends(workspace_user)):
    return await store.create_project(request.state.db, user["workspace_id"], data.model_dump())


@project_router.get("/{project_id}")
async def get_project(project_id: int, request: Request, user: dict = Depends(workspace_user)):
    project = await store.get_project(request.state.db, user["workspace_id"], project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    return project


@project_router.patch("/{project_id}")
async def update_project(project_id: int, data: ProjectUpdate, request: Request, user: dict = Depends(workspace_user)):
    project = await store.update_project(
        request.state.db, user["workspace_id"], project_id, data.model_dump(exclude_unset=True)
    )
    if project is None:
        raise HTTPException(404, "Project not found")
    return project


@project_router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: int, request: Request, user: dict = Depends(workspace_user)):
    deleted = await store.delete_project(request.state.db, request.state.blobs, user["workspace_id"], project_id)
    if not deleted:
        raise HTTPException(404, "Project not found")
    return Response(status_code=204)


@project_router.get("/{project_id}/export")
async def export_project(project_id: int, request: Request, user: dict = Depends(workspace_user)):
    project = await store.get_project(request.state.db, user["workspace_id"], project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    tasks = await store.list_tasks(request.state.db, user["workspace_id"], project_id)
    costs = await store.list_costs(request.state.db, user["workspace_id"], project_id)
    try:
        content = excel_export.export_project_workbook(project, tasks, costs)
    except Exception as exc:
        raise HTTPException(500, f"export failed: {exc}") from exc
    safe = "".join(ch for ch in project["name"] if ch.isascii() and ch not in "\"\\/") or "project"
    filename = f"project-{project_id}-{safe}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@project_router.get("/{project_id}/tasks")
async def list_tasks(project_id: int, request: Request, user: dict = Depends(workspace_user)):
    if await store.get_project(request.state.db, user["workspace_id"], project_id) is None:
        raise HTTPException(404, "Project not found")
    return await store.list_tasks(request.state.db, user["workspace_id"], project_id)


@project_router.post("/{project_id}/tasks", status_code=201)
async def create_task(project_id: int, data: TaskCreate, request: Request, user: dict = Depends(workspace_user)):
    try:
        return await store.create_task(
            request.state.db, user["workspace_id"], project_id, data.model_dump()
        )
    except (LookupError, Conflict, ValueError) as exc:
        raise_mapped(exc)


@project_router.get("/{project_id}/dependencies")
async def list_dependencies(project_id: int, request: Request, user: dict = Depends(workspace_user)):
    if await store.get_project(request.state.db, user["workspace_id"], project_id) is None:
        raise HTTPException(404, "Project not found")
    return await store.list_dependencies(request.state.db, user["workspace_id"], project_id)


@project_router.get("/{project_id}/costs")
async def list_costs(project_id: int, request: Request, user: dict = Depends(workspace_user)):
    if await store.get_project(request.state.db, user["workspace_id"], project_id) is None:
        raise HTTPException(404, "Project not found")
    return await store.list_costs(request.state.db, user["workspace_id"], project_id)


@task_router.get("/api/tasks/{task_id}")
async def get_task(task_id: int, request: Request, user: dict = Depends(workspace_user)):
    task = await store.get_task(request.state.db, user["workspace_id"], task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    return task


@task_router.patch("/api/tasks/{task_id}")
async def update_task(task_id: int, data: TaskUpdate, request: Request, user: dict = Depends(workspace_user)):
    try:
        task = await store.update_task(
            request.state.db, user["workspace_id"], task_id, data.model_dump(exclude_unset=True)
        )
    except (Conflict, ValueError) as exc:
        raise_mapped(exc)
    if task is None:
        raise HTTPException(404, "Task not found")
    return task


@task_router.post("/api/tasks/{task_id}/move")
async def move_task(task_id: int, data: TaskMove, request: Request, user: dict = Depends(workspace_user)):
    task = await store.move_task(
        request.state.db, user["workspace_id"], task_id, data.start_date, data.end_date
    )
    if task is None:
        raise HTTPException(404, "Task not found")
    return task


@task_router.delete("/api/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int, request: Request, user: dict = Depends(workspace_user)):
    deleted = await store.delete_task(request.state.db, request.state.blobs, user["workspace_id"], task_id)
    if not deleted:
        raise HTTPException(404, "Task not found")
    return Response(status_code=204)


@task_router.post("/api/tasks/{task_id}/dependencies")
async def add_dependency(
    task_id: int,
    data: DependencyCreate,
    request: Request,
    response: Response,
    user: dict = Depends(workspace_user),
):
    try:
        dependency, created = await store.add_dependency(
            request.state.db,
            user["workspace_id"],
            task_id,
            data.predecessor_id,
            data.dep_type,
        )
    except (LookupError, ValueError) as exc:
        raise_mapped(exc)
    if created:
        response.status_code = 201
    return dependency


@task_router.delete("/api/dependencies/{dependency_id}", status_code=204)
async def delete_dependency(dependency_id: int, request: Request, user: dict = Depends(workspace_user)):
    deleted = await store.delete_dependency(request.state.db, user["workspace_id"], dependency_id)
    if not deleted:
        raise HTTPException(404, "Dependency not found")
    return Response(status_code=204)


@cost_router.post("/api/costs", status_code=201)
async def create_cost(data: CostCreate, request: Request, user: dict = Depends(workspace_user)):
    try:
        return await store.create_cost(request.state.db, user["workspace_id"], data.model_dump())
    except (LookupError, ValueError) as exc:
        raise_mapped(exc)


@cost_router.patch("/api/costs/{cost_id}")
async def update_cost(cost_id: int, data: CostUpdate, request: Request, user: dict = Depends(workspace_user)):
    try:
        cost = await store.update_cost(
            request.state.db, user["workspace_id"], cost_id, data.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise_mapped(exc)
    if cost is None:
        raise HTTPException(404, "Cost not found")
    return cost


@cost_router.delete("/api/costs/{cost_id}", status_code=204)
async def delete_cost(cost_id: int, request: Request, user: dict = Depends(workspace_user)):
    deleted = await store.delete_cost(request.state.db, request.state.blobs, user["workspace_id"], cost_id)
    if not deleted:
        raise HTTPException(404, "Cost not found")
    return Response(status_code=204)


@stats_router.get("/costs")
async def cost_stats(request: Request, project_id: int | None = None, user: dict = Depends(workspace_user)):
    try:
        return await store.cost_stats(request.state.db, user["workspace_id"], project_id)
    except LookupError as exc:
        raise_mapped(exc)


@stats_router.get("/overview")
async def overview(request: Request, user: dict = Depends(workspace_user)):
    return await store.overview(request.state.db, user["workspace_id"])


@inbox_router.get("")
async def list_inbox(request: Request, kind: str | None = None, user: dict = Depends(workspace_user)):
    if kind is not None and kind not in ("interrupt", "idea"):
        raise HTTPException(400, "kind 无效")
    return await store.list_inbox(request.state.db, user["workspace_id"], kind)


@inbox_router.post("", status_code=201)
async def create_inbox(data: InboxCreate, request: Request, user: dict = Depends(workspace_user)):
    try:
        return await store.create_inbox(request.state.db, user["workspace_id"], data.model_dump())
    except ValueError as exc:
        raise_mapped(exc)


@inbox_router.patch("/{item_id}")
async def update_inbox(item_id: int, data: InboxUpdate, request: Request, user: dict = Depends(workspace_user)):
    try:
        item = await store.update_inbox(
            request.state.db, user["workspace_id"], item_id, data.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise_mapped(exc)
    if item is None:
        raise HTTPException(404, "Inbox item not found")
    return item


@inbox_router.post("/{item_id}/promote")
async def promote_inbox(item_id: int, data: InboxPromote, request: Request, user: dict = Depends(workspace_user)):
    try:
        item = await store.promote_inbox(
            request.state.db, user["workspace_id"], item_id, data.model_dump()
        )
    except ValueError as exc:
        raise_mapped(exc)
    if item is None:
        raise HTTPException(404, "Inbox item not found")
    return item


@inbox_router.delete("/{item_id}", status_code=204)
async def delete_inbox(item_id: int, request: Request, user: dict = Depends(workspace_user)):
    deleted = await store.delete_inbox(request.state.db, request.state.blobs, user["workspace_id"], item_id)
    if not deleted:
        raise HTTPException(404, "Inbox item not found")
    return Response(status_code=204)


@category_router.get("")
async def list_categories(request: Request, user: dict = Depends(workspace_user)):
    return await store.list_categories(request.state.db, user["workspace_id"])


@category_router.post("", status_code=201)
async def create_category(data: CostCategoryCreate, request: Request, user: dict = Depends(workspace_user)):
    try:
        return await store.create_category(request.state.db, user["workspace_id"], data.model_dump())
    except Conflict as exc:
        raise_mapped(exc)


@category_router.patch("/{category_id}")
async def update_category(
    category_id: int,
    data: CostCategoryUpdate,
    request: Request,
    user: dict = Depends(workspace_user),
):
    try:
        category = await store.update_category(
            request.state.db, user["workspace_id"], category_id, data.model_dump(exclude_unset=True)
        )
    except Conflict as exc:
        raise_mapped(exc)
    if category is None:
        raise HTTPException(404, "Category not found")
    return category


@category_router.delete("/{category_id}", status_code=204)
async def delete_category(category_id: int, request: Request, user: dict = Depends(workspace_user)):
    try:
        deleted = await store.delete_category(request.state.db, user["workspace_id"], category_id)
    except Conflict as exc:
        raise_mapped(exc)
    if not deleted:
        raise HTTPException(404, "Category not found")
    return Response(status_code=204)


def _attachment_public(row: dict) -> dict:
    return {key: row[key] for key in ("id", "entity_type", "entity_id", "original_name", "mime", "size", "uploaded_at")}


@attachment_router.get("/{attachment_id}/download")
async def download_attachment(attachment_id: int, request: Request, user: dict = Depends(workspace_user)):
    row = await store.get_attachment(request.state.db, user["workspace_id"], attachment_id)
    if row is None:
        raise HTTPException(404, "附件不存在")
    from app.blobs import object_key

    data = await request.state.blobs.get(object_key(user["workspace_id"], row["stored_path"]))
    if data is None:
        raise HTTPException(404, "附件文件已丢失")
    filename = quote(row["original_name"])
    return Response(
        content=data,
        media_type=row["mime"] or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@attachment_router.get("/{attachment_id}")
async def get_attachment(attachment_id: int, request: Request, user: dict = Depends(workspace_user)):
    row = await store.get_attachment(request.state.db, user["workspace_id"], attachment_id)
    if row is None:
        raise HTTPException(404, "附件不存在")
    return _attachment_public(row)


@attachment_router.delete("/{attachment_id}", status_code=204)
async def delete_attachment(attachment_id: int, request: Request, user: dict = Depends(workspace_user)):
    deleted = await store.delete_attachment(
        request.state.db, request.state.blobs, user["workspace_id"], attachment_id
    )
    if not deleted:
        raise HTTPException(404, "附件不存在")
    return Response(status_code=204)


@attachment_router.post("/{entity_type}/{entity_id}", status_code=201)
async def upload_attachment(
    request: Request,
    entity_type: str = Path(..., pattern="^(task|cost|inbox)$"),
    entity_id: int = Path(...),
    file: UploadFile = File(...),
    user: dict = Depends(workspace_user),
):
    content = await file.read(store.MAX_FILE_BYTES + 1)
    try:
        return await store.save_attachment(
            request.state.db,
            request.state.blobs,
            user["workspace_id"],
            entity_type,
            entity_id,
            file.filename or "file",
            file.content_type,
            content,
        )
    except (LookupError, PayloadTooLarge, ValueError) as exc:
        raise_mapped(exc)


@attachment_router.get("/{entity_type}/{entity_id}")
async def list_attachments(
    request: Request,
    entity_type: str = Path(..., pattern="^(task|cost|inbox)$"),
    entity_id: int = Path(...),
    user: dict = Depends(workspace_user),
):
    try:
        return await store.list_attachments(request.state.db, user["workspace_id"], entity_type, entity_id)
    except ValueError as exc:
        raise_mapped(exc)
