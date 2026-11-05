"""Request bodies. Response shapes match the personal-pm JSON the Vue client already speaks."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

PROJECT_STATUSES = {"active", "archived"}
TASK_STATUSES = {"todo", "progress", "delayed", "done", "cancelled"}
PRIORITIES = {"low", "normal", "high", "urgent"}
DEP_TYPES = {"FS", "SS", "FF", "SF"}
INBOX_KINDS = {"interrupt", "idea"}
INBOX_STATUSES = {"active", "completed", "archived"}
ROLES = {"admin", "user"}


def normalize_email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 200 or "@" not in value:
        raise ValueError("邮箱格式不正确")
    local, _, domain = value.partition("@")
    if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise ValueError("邮箱格式不正确")
    return value


class LoginIn(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return normalize_email(value)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=10, max_length=200)
    display_name: str | None = Field(default=None, max_length=100)
    role: str = "user"
    workspace_id: int | None = None

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("role")
    @classmethod
    def _role(cls, value: str) -> str:
        if value not in ROLES:
            raise ValueError("角色无效")
        return value


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: str | None = None
    workspace_id: int | None = None
    password: str | None = Field(default=None, min_length=10, max_length=200)

    @field_validator("role")
    @classmethod
    def _role(cls, value: str | None) -> str | None:
        if value is not None and value not in ROLES:
            raise ValueError("角色无效")
        return value


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class WorkspaceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str = Field(default="#0071e3", max_length=20)
    description: str | None = Field(default=None, max_length=2000)
    start_date: date | None = None
    end_date: date | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=2000)
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def _status(cls, value: str | None) -> str | None:
        if value is not None and value not in PROJECT_STATUSES:
            raise ValueError("项目状态无效")
        return value


class TaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    parent_id: int | None = None
    status: str = "todo"
    priority: str = "normal"
    start_date: date | None = None
    end_date: date | None = None
    progress: int = Field(0, ge=0, le=100)
    is_milestone: bool = False
    sort_order: int = 0
    project_id: int | None = None

    @field_validator("status")
    @classmethod
    def _status(cls, value: str) -> str:
        if value not in TASK_STATUSES:
            raise ValueError("任务状态无效")
        return value

    @field_validator("priority")
    @classmethod
    def _priority(cls, value: str) -> str:
        if value not in PRIORITIES:
            raise ValueError("优先级无效")
        return value


class TaskUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    parent_id: int | None = None
    status: str | None = None
    priority: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    progress: int | None = Field(None, ge=0, le=100)
    is_milestone: bool | None = None
    sort_order: int | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _name(cls, value):
        if value is None:
            raise ValueError("name cannot be null")
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("name cannot be empty")
        return value

    @field_validator("status")
    @classmethod
    def _status(cls, value: str | None) -> str | None:
        if value is not None and value not in TASK_STATUSES:
            raise ValueError("任务状态无效")
        return value

    @field_validator("priority")
    @classmethod
    def _priority(cls, value: str | None) -> str | None:
        if value is not None and value not in PRIORITIES:
            raise ValueError("优先级无效")
        return value


class TaskMove(BaseModel):
    start_date: date
    end_date: date


class DependencyCreate(BaseModel):
    predecessor_id: int
    dep_type: str = Field(default="FS", max_length=10)

    @field_validator("dep_type")
    @classmethod
    def _dep(cls, value: str) -> str:
        if value not in DEP_TYPES:
            raise ValueError("依赖类型无效")
        return value


class CostCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(default="other", max_length=50)
    amount: float = Field(gt=0)
    description: str | None = None
    spent_at: date
    task_id: int | None = None
    project_id: int

    @field_validator("name", mode="before")
    @classmethod
    def _name(cls, value):
        if value is None:
            raise ValueError("name cannot be null")
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("name cannot be empty")
        return value


class CostUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=50)
    amount: float | None = Field(default=None, gt=0)
    description: str | None = None
    spent_at: date | None = None
    task_id: int | None = None
    project_id: int | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _name(cls, value):
        if value is None:
            raise ValueError("name cannot be null")
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("name cannot be empty")
        return value


class InboxCreate(BaseModel):
    kind: str = Field(default="idea", pattern="^(interrupt|idea)$")
    title: str = Field(min_length=1, max_length=200)
    notes: str | None = None
    priority: str = Field(default="normal", max_length=20)
    due_at: datetime | None = None
    project_id: int | None = None

    @field_validator("priority")
    @classmethod
    def _priority(cls, value: str) -> str:
        if value not in PRIORITIES:
            raise ValueError("优先级无效")
        return value


class InboxUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = None
    priority: str | None = None
    due_at: datetime | None = None
    project_id: int | None = None
    status: str | None = Field(default=None, pattern="^(active|completed|archived)$")

    @field_validator("priority")
    @classmethod
    def _priority(cls, value: str | None) -> str | None:
        if value is not None and value not in PRIORITIES:
            raise ValueError("优先级无效")
        return value


class InboxPromote(BaseModel):
    project_id: int | None = None
    name: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class CostCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(default="#8e8e93", pattern="^#[0-9a-fA-F]{6}$")
    sort_order: int = 0


class CostCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, pattern="^#[0-9a-fA-F]{6}$")
    sort_order: int | None = None
