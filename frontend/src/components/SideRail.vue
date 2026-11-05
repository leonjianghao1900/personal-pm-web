<template>
 <aside class="glass-card md:sticky md:top-5 p-2 md:p-3 flex flex-row md:flex-col items-center gap-1 self-start overflow-x-auto">
 <div class="w-12 h-12 rounded-2xl flex items-center justify-center text-2xl font-bold shrink-0">
 <span class="bg-gradient-to-br from-apple-blue to-apple-purple bg-clip-text text-transparent">◉</span>
 </div>
 <div class="hidden md:block w-8 h-px bg-black/10 dark:bg-white/10 my-1"></div>
 <template v-if="canUsePm">
 <RailIcon v-for="item in mainItems" :key="item.path" :to="item.path" :icon="item.icon"
 :active="isActive(item.path)" :title="item.label" />
 </template>
 <div class="hidden md:block w-8 h-px bg-black/10 dark:bg-white/10 my-1"></div>
 <RailIcon v-if="auth.isAdmin" to="/admin/workspaces" icon="🏢" title="工作区" :active="isActive('/admin/workspaces')" />
 <RailIcon v-if="auth.isAdmin" to="/admin/users" icon="👥" title="用户" :active="isActive('/admin/users')" />
 <RailIcon to="/settings" icon="⚙" title="系统管理" :active="isActive('/settings')" />
 </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import RailIcon from './RailIcon.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()
const canUsePm = computed(() => Boolean(auth.user?.workspace_id))
const mainItems = [
 { path: '/dashboard', icon: '📊', label: '总览仪表盘' },
 { path: '/gantt', icon: '📅', label: '甘特图' },
 { path: '/tasks', icon: '✅', label: '任务管理' },
 { path: '/costs', icon: '💰', label: '费用记录' },
 { path: '/inbox', icon: '📥', label: '临时收件箱' }
]

function isActive(path: string) {
 return route.path === path || route.path.startsWith(path + '/')
}
</script>
