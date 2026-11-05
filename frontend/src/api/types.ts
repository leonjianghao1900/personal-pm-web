export type ProjectStatus = 'active' | 'archived'
export type TaskStatus = 'todo' | 'progress' | 'delayed' | 'done' | 'cancelled'
export type Priority = 'low' | 'normal' | 'high' | 'urgent'
export type BuiltinCostCategory = 'material' | 'labor' | 'travel' | 'other'
export type InboxKind = 'interrupt' | 'idea'
export type InboxStatus = 'active' | 'completed' | 'archived'

export interface Project {
  id: number
  name: string
  color: string
  description: string | null
  start_date: string | null
  end_date: string | null
  status: ProjectStatus
  task_count: number
  created_at: string
  updated_at: string
}

export interface Task {
  id: number
  project_id: number
  parent_id: number | null
  name: string
  description: string | null
  status: TaskStatus
  priority: Priority
  start_date: string | null
  end_date: string | null
  progress: number
  sort_order: number
  is_milestone: boolean
  created_at: string
  updated_at: string
}

export interface TaskDependency {
  id: number
  predecessor_id: number
  successor_id: number
  dep_type: string
  created_at: string
}

export interface Cost {
  id: number
  project_id: number
  task_id: number | null
  name: string
  category: string
  amount: number
  description: string | null
  spent_at: string
  created_at: string
}

export interface CostStats {
  total: number
  count: number
  by_category: Record<string, number>
  by_month: Record<string, number>
}

export interface InboxItem {
  id: number
  kind: InboxKind
  title: string
  notes: string | null
  priority: Priority
  due_at: string | null
  project_id: number | null
  promoted_task_id: number | null
  status: InboxStatus
  created_at: string
  completed_at: string | null
}

export interface CostCategory {
  id: number
  name: string
  color: string
  is_builtin: boolean
  sort_order: number
}

export interface SessionUser {
  id: number
  email: string
  display_name: string
  role: 'admin' | 'user'
  workspace_id: number | null
  workspace_name: string | null
  must_rotate_password: boolean
  created_at: string
}

export interface Workspace {
  id: number
  name: string
  member_count: number
  created_at: string
  updated_at: string
}
