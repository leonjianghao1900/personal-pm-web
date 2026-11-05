import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/login', meta: { public: true, bare: true }, component: () => import('@/views/LoginView.vue') },
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: () => import('@/views/DashboardView.vue') },
  { path: '/gantt', component: () => import('@/views/GanttView.vue') },
  { path: '/gantt/:projectId/task/:taskId', component: () => import('@/views/TaskDetailView.vue') },
  { path: '/tasks', component: () => import('@/views/ProjectListView.vue') },
  { path: '/costs', component: () => import('@/views/CostsView.vue') },
  { path: '/inbox', component: () => import('@/views/InboxView.vue') },
  { path: '/settings', meta: { allowNoWorkspace: true }, component: () => import('@/views/SettingsView.vue') },
  { path: '/admin/users', meta: { admin: true, allowNoWorkspace: true }, component: () => import('@/views/AdminUsersView.vue') },
  { path: '/admin/workspaces', meta: { admin: true, allowNoWorkspace: true }, component: () => import('@/views/AdminWorkspacesView.vue') },
  { path: '/awaiting', meta: { allowNoWorkspace: true }, component: () => import('@/views/AwaitingView.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' }
]

export const router = createRouter({
  history: createWebHistory(),
  routes
})

function homeFor(user: { role: string; workspace_id: number | null }) {
  if (user.workspace_id) return '/dashboard'
  return user.role === 'admin' ? '/admin/workspaces' : '/awaiting'
}

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.loaded) await auth.fetchMe()
  const user = auth.user
  if (to.meta.public) {
    if (user && to.path === '/login') return homeFor(user)
    return true
  }
  if (!user) {
    return { path: '/login', query: { next: to.fullPath } }
  }
  if (to.meta.admin && user.role !== 'admin') return homeFor(user)
  if (!user.workspace_id && !to.meta.allowNoWorkspace) return homeFor(user)
  return true
})
