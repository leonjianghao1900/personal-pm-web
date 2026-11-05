<template>
 <GlassCard class="flex flex-wrap items-center justify-between gap-3 px-4 md:px-5 py-3">
 <div class="flex items-center gap-3">
 <div class="text-lg font-bold bg-gradient-to-r from-apple-blue to-apple-purple bg-clip-text text-transparent">
 📋 个人 PM
 </div>
 <div class="relative" ref="menuRef">
 <button @click.stop="toggleMenu"
 ref="triggerRef"
 :class="['flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-semibold border transition',
 currentProject
 ? 'bg-white/70 dark:bg-white/15 border-black/5 dark:border-white/10 hover:bg-white'
 : 'bg-apple-blue/10 border-apple-blue/20 text-apple-blue hover:bg-apple-blue/15']">
 <span v-if="currentProject" class="w-3 h-3 rounded-full" :style="{ background: currentProject.color }"></span>
 <span>{{ currentProject?.name ?? '选择项目' }}</span>
 <span class="text-gray-400 dark:text-gray-500">▾</span>
 </button>
 </div>
 <Teleport to="body">
 <div v-if="showMenu"
 :style="menuPosition"
 class="fixed z-[1000] w-60 max-h-80 overflow-auto rounded-xl bg-white shadow-xl border border-black/10 dark:border-white/15 py-1">
 <div v-if="projects.projects.length === 0" class="px-3 py-3 text-sm text-gray-400 dark:text-gray-500 text-center">
 还没有项目
 </div>
 <button v-for="p in projects.projects" :key="p.id"
 @click="onSelect(p.id)"
 :class="['w-full text-left px-3 py-2 text-sm flex items-center gap-2 hover:bg-black/5 dark:hover:bg-white/10 dark:bg-white/10',
 projects.currentId === p.id ? 'bg-apple-blue/10 font-semibold' : '']">
 <span class="w-3 h-3 rounded-full shrink-0" :style="{ background: p.color }"></span>
 <span class="flex-1 truncate">{{ p.name }}</span>
 <span v-if="projects.currentId === p.id" class="text-apple-blue text-xs">✓</span>
 </button>
 <div v-if="projects.projects.length > 0" class="border-t border-black/5 dark:border-white/10 my-1"></div>
 <RouterLink to="/tasks"
 @click="showMenu = false"
 class="w-full text-left px-3 py-2 text-sm hover:bg-black/5 dark:hover:bg-white/10 dark:bg-white/10 text-gray-600 flex items-center gap-2 block">
 📁 管理项目...
 </RouterLink>
 </div>
 </Teleport>
 </div>
 <nav class="flex flex-wrap gap-1">
 <RouterLink v-for="n in nav" :key="n.path" :to="n.path"
 :class="['px-3 py-1.5 rounded-lg text-sm font-medium transition',
 isActive(n.path)
 ? 'bg-apple-blue/15 text-apple-blue'
 : 'text-gray-500 dark:text-gray-400 hover:bg-black/5 dark:hover:bg-white/10 dark:bg-white/10 dark:hover:bg-white/10 dark:bg-white/[0.04]']">
 {{ n.label }}
 </RouterLink>
 </nav>
 <div class="flex flex-wrap items-center gap-2">
 <div v-if="auth.user" class="text-right leading-tight">
 <div class="text-sm font-medium max-w-[10rem] truncate">{{ auth.user.display_name }}</div>
 <div class="text-[11px] text-gray-400 truncate max-w-[12rem]">
 {{ auth.user.workspace_name || (auth.isAdmin ? '未加入工作区' : auth.user.email) }}
 </div>
 </div>
 <button @click="onLogout"
 class="px-2.5 h-8 rounded-lg bg-white/60 dark:bg-white/10 border border-black/5 dark:border-white/10 text-sm">
 退出
 </button>
 <button @click="toggleTheme"
 class="w-8 h-8 rounded-lg bg-white/60 dark:bg-white/10 border border-black/5 dark:border-white/10 hover:bg-white dark:hover:bg-white/20 dark:bg-white/[0.03] transition"
 :title="isDark ? '切换到浅色' : '切换到深色'">
 {{ isDark ? '☀️' : '🌙' }}
 </button>
 </div>
 </GlassCard>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import GlassCard from './GlassCard.vue'
import { useRoute } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const projects = useProjectsStore()
const auth = useAuthStore()

async function onLogout() {
  await auth.logout()
  window.location.assign('/login')
}

const currentProject = computed(() => projects.current)

const nav = [
 { path: '/dashboard', label: '总览' },
 { path: '/gantt', label: '甘特图' },
 { path: '/tasks', label: '任务' },
 { path: '/costs', label: '费用' },
 { path: '/inbox', label: '收件箱' }
]

function isActive(path: string) {
 return route.path === path || route.path.startsWith(path + '/')
}

const showMenu = ref(false)
const menuRef = ref<HTMLElement | null>(null)
const triggerRef = ref<HTMLElement | null>(null)
const menuPosition = ref({ top: '0px', left: '0px' })

function toggleMenu() {
 if (showMenu.value) {
 showMenu.value = false
 return
 }
 if (triggerRef.value) {
 const rect = triggerRef.value.getBoundingClientRect()
 menuPosition.value = {
 top: `${rect.bottom + 4}px`,
 left: `${rect.left}px`
 }
 }
 showMenu.value = true
}

function onSelect(id: number) {
 projects.select(id)
 showMenu.value = false
}

function handleClickOutside(e: MouseEvent) {
 if (!showMenu.value) return
 const target = e.target as Node
 if (menuRef.value && menuRef.value.contains(target)) return
 const trigger = (triggerRef.value as any)?.$el ?? triggerRef.value
 if (trigger && trigger.contains(target)) return
 showMenu.value = false
}

// 主题切换
const isDark = ref(false)
const THEME_KEY = 'pm-theme'

function applyTheme(dark: boolean) {
 isDark.value = dark
 if (dark) document.documentElement.classList.add('dark')
 else document.documentElement.classList.remove('dark')
}

function toggleTheme() {
 applyTheme(!isDark.value)
 try { localStorage.setItem(THEME_KEY, isDark.value ? 'dark' : 'light') } catch {}
}

onMounted(() => {
 let saved: string | null = null
 try { saved = localStorage.getItem(THEME_KEY) } catch {}
 const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches
 applyTheme(saved === 'dark' || (saved === null && prefersDark))
 document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
 document.removeEventListener('click', handleClickOutside)
})
</script>