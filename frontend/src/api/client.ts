import axios from 'axios'
import type { Cost, CostCategory, CostStats, InboxItem, InboxKind, Project, SessionUser, Task, TaskDependency, Workspace } from './types'

declare module 'axios' {
  export interface AxiosRequestConfig {
    skipAlert?: boolean
  }
  export interface InternalAxiosRequestConfig {
    skipAlert?: boolean
  }
}

const api = axios.create({ baseURL: '/api', withCredentials: true })

api.interceptors.response.use(
  r => r,
  err => {
    const status = err.response?.status
    const url = String(err.config?.url || '')
    if (status === 401) {
      const quiet = url.includes('/auth/login') || url.includes('/auth/me')
      if (!quiet && !window.location.pathname.startsWith('/login')) {
        const next = window.location.pathname + window.location.search
        window.location.assign('/login?next=' + encodeURIComponent(next))
      }
      return Promise.reject(err)
    }
    if (!err.config?.skipAlert) {
      const detail = err.response?.data?.detail
      const detailText = typeof detail === 'string' ? detail : ''
      const msg = status
        ? `请求失败 (${status})${detailText ? ': ' + detailText : ''}`
        : '网络错误，请确认后端服务已启动'
      window.alert(msg)
    }
    return Promise.reject(err)
  }
)

export type TaskInput = Partial<
  Pick<
    Task,
    | 'name' | 'description' | 'parent_id' | 'status' | 'priority'
    | 'start_date' | 'end_date' | 'progress' | 'is_milestone' | 'sort_order'
  >
>

export const projectsApi = {
  list: () => api.get<Project[]>('/projects').then(r => r.data),
  get: (id: number) => api.get<Project>(`/projects/${id}`).then(r => r.data),
  create: (data: Partial<Pick<Project, 'name' | 'color' | 'description' | 'start_date' | 'end_date' | 'status'>>) =>
    api.post<Project>('/projects', data).then(r => r.data),
  update: (id: number, data: Partial<Pick<Project, 'name' | 'color' | 'description' | 'start_date' | 'end_date' | 'status'>>) =>
    api.patch<Project>(`/projects/${id}`, data).then(r => r.data),
  remove: (id: number) => api.delete(`/projects/${id}`).then(() => undefined),
  export: async (id: number, name: string) => {
    const r = await api.get<Blob>(`/projects/${id}/export`, { responseType: 'blob' })
    const url = URL.createObjectURL(r.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `project-${id}-${name}.xlsx`
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
}

export const tasksApi = {
  listByProject: (projectId: number) =>
    api.get<Task[]>(`/projects/${projectId}/tasks`).then(r => r.data),
  get: (id: number) => api.get<Task>(`/tasks/${id}`).then(r => r.data),
  create: (projectId: number, data: TaskInput) =>
    api.post<Task>(`/projects/${projectId}/tasks`, data).then(r => r.data),
  update: (id: number, data: TaskInput) =>
    api.patch<Task>(`/tasks/${id}`, data).then(r => r.data),
  move: (id: number, start_date: string, end_date: string) =>
    api.post<Task>(`/tasks/${id}/move`, { start_date, end_date }).then(r => r.data),
  remove: (id: number) => api.delete(`/tasks/${id}`).then(() => undefined)
}

export const depsApi = {
  listByProject: (projectId: number) =>
    api.get<TaskDependency[]>(`/projects/${projectId}/dependencies`).then(r => r.data),
  add: (taskId: number, predecessorId: number) =>
    api.post<TaskDependency>(`/tasks/${taskId}/dependencies`, { predecessor_id: predecessorId })
      .then(r => r.data),
  remove: (id: number) => api.delete(`/dependencies/${id}`).then(() => undefined)
}

export type CostCreateInput =
  Pick<Cost, 'name' | 'category' | 'amount' | 'spent_at'> &
  Partial<Pick<Cost, 'description' | 'task_id'>>

export type CostUpdateInput = Partial<
  Pick<Cost, 'name' | 'category' | 'amount' | 'description' | 'spent_at' | 'task_id' | 'project_id'>
>

export const costsApi = {
  listByProject: (projectId: number) =>
    api.get<Cost[]>(`/projects/${projectId}/costs`).then(r => r.data),
  create: (projectId: number, data: CostCreateInput) =>
    api.post<Cost>('/costs', { ...data, project_id: projectId }).then(r => r.data),
  update: (id: number, data: CostUpdateInput) =>
    api.patch<Cost>(`/costs/${id}`, data).then(r => r.data),
  remove: (id: number) => api.delete(`/costs/${id}`).then(() => undefined),
  stats: (projectId?: number) =>
    api.get<CostStats>('/stats/costs', { params: projectId ? { project_id: projectId } : {} })
      .then(r => r.data)
}

export type InboxInput = Partial<
  Pick<InboxItem, 'kind' | 'title' | 'notes' | 'priority' | 'due_at' | 'project_id' | 'status'>
>

export const inboxApi = {
  list: (kind?: InboxKind) =>
    api.get<InboxItem[]>('/inbox', { params: kind ? { kind } : {} }).then(r => r.data),
  create: (data: InboxInput) => api.post<InboxItem>('/inbox', data).then(r => r.data),
  update: (id: number, data: InboxInput) =>
    api.patch<InboxItem>(`/inbox/${id}`, data).then(r => r.data),
  promote: (id: number, data: { project_id?: number; name?: string }) =>
    api.post<InboxItem>(`/inbox/${id}/promote`, data).then(r => r.data),
  remove: (id: number) => api.delete(`/inbox/${id}`).then(() => undefined)
}

export const categoriesApi = {
  list: () => api.get<CostCategory[]>('/cost-categories').then(r => r.data),
  create: (data: { name: string; color: string }) =>
    api.post<CostCategory>('/cost-categories', data).then(r => r.data),
  update: (id: number, data: Partial<Pick<CostCategory, 'name' | 'color' | 'sort_order'>>) =>
    api.patch<CostCategory>(`/cost-categories/${id}`, data).then(r => r.data),
  remove: (id: number) => api.delete(`/cost-categories/${id}`).then(() => undefined)
}

export interface OverviewProject {
  id: number
  name: string
  color: string
  task_total: number
  task_done: number
  progress: number
  next_due_task: { id: number; name: string; end_date: string } | null
}

export interface Overview {
  project_count: number
  active_task_count: number
  delayed_task_count: number
  this_month_cost: number
  projects: OverviewProject[]
}

export const statsApi = {
  overview: () => api.get<Overview>('/stats/overview').then(r => r.data)
}

export const adminApi = {
  backup: () => api.get<Blob>('/admin/backup', { responseType: 'blob' }).then(r => r.data),
  restore: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post<{ status: string; counts: Record<string, number> }>('/admin/restore', fd)
      .then(r => r.data)
  },
  backupFull: () => api.get<Blob>('/admin/backup/full', { responseType: 'blob' }).then(r => r.data),
  restoreFull: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post<{ status: string; counts: Record<string, number> }>('/admin/restore/full', fd)
      .then(r => r.data)
  }
}

export interface Attachment {
  id: number
  entity_type: 'task' | 'cost' | 'inbox'
  entity_id: number
  original_name: string
  mime: string
  size: number
  uploaded_at: string
}

export type EntityType = 'task' | 'cost' | 'inbox'

export const attachmentsApi = {
  list: (entityType: EntityType, entityId: number) =>
    api.get<Attachment[]>(`/attachments/${entityType}/${entityId}`).then(r => r.data),
  upload: (entityType: EntityType, entityId: number, file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post<Attachment>(`/attachments/${entityType}/${entityId}`, fd)
      .then(r => r.data)
  },
  downloadUrl: (id: number) => `/api/attachments/${id}/download`,
  remove: (id: number) => api.delete(`/attachments/${id}`).then(() => undefined)
}

export const ATTACHMENT_LIMITS: Record<EntityType, number> = {
  task: 10,
  cost: 5,
  inbox: 5,
}

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export interface UpdateInfo {
  current_version: string
  latest_version: string | null
  has_update: boolean
  release_url: string
  release_notes: string | null
  assets: { name: string; size: number; url: string }[]
  checked_at: string
}

export const updatesApi = {
  check: (force = false) =>
    api.get<UpdateInfo>('/updates/check', { params: force ? { force: 1 } : {} })
      .then(r => r.data),
}

export const authApi = {
  login: (email: string, password: string) =>
    api.post<{ user: SessionUser }>('/auth/login', { email, password }, { skipAlert: true }).then(r => r.data),
  logout: () => api.post('/auth/logout', {}, { skipAlert: true }).then(() => undefined),
  me: () => api.get<SessionUser>('/auth/me', { skipAlert: true }).then(r => r.data),
  changePassword: (current_password: string, new_password: string) =>
    api.post<SessionUser>('/auth/change-password', { current_password, new_password }).then(r => r.data),
}

export const directoryApi = {
  users: () => api.get<SessionUser[]>('/admin/users').then(r => r.data),
  createUser: (data: {
    email: string
    password: string
    display_name?: string
    role: 'admin' | 'user'
    workspace_id?: number | null
  }) => api.post<SessionUser>('/admin/users', data).then(r => r.data),
  updateUser: (id: number, data: {
    display_name?: string
    role?: 'admin' | 'user'
    workspace_id?: number | null
    password?: string
  }) => api.patch<SessionUser>(`/admin/users/${id}`, data).then(r => r.data),
  removeUser: (id: number) => api.delete(`/admin/users/${id}`).then(() => undefined),
  workspaces: () => api.get<Workspace[]>('/admin/workspaces').then(r => r.data),
  createWorkspace: (name: string) => api.post<Workspace>('/admin/workspaces', { name }).then(r => r.data),
  updateWorkspace: (id: number, name: string) =>
    api.patch<Workspace>(`/admin/workspaces/${id}`, { name }).then(r => r.data),
  removeWorkspace: (id: number) => api.delete(`/admin/workspaces/${id}`).then(() => undefined),
}
