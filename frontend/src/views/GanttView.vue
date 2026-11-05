<template>
 <GlassCard class="p-5">
 <div class="flex items-center justify-between mb-4">
 <div class="flex items-center gap-3">
 <div class="relative" ref="projectMenuRef">
 <button @click.stop="toggleProjectMenu"
 ref="projectMenuTrigger"
 class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/70 dark:bg-white/15 border border-black/5 dark:border-white/10 text-sm font-semibold hover:bg-white">
 <span v-if="currentProject" class="w-3 h-3 rounded-full" :style="{ background: currentProject.color }"></span>
 <span>{{ currentProject?.name ?? '选择项目' }}</span>
 <span class="text-gray-400 dark:text-gray-500">▾</span>
 </button>
 </div>
 <Teleport to="body">
 <div v-if="projectMenuOpen"
 :style="projectMenuPosition"
 class="fixed z-[1000] w-60 max-h-80 overflow-auto rounded-xl bg-white shadow-xl border border-black/10 dark:border-white/15 py-1">
 <div v-if="projects.projects.length === 0" class="px-3 py-3 text-sm text-gray-400 dark:text-gray-500 text-center">
 还没有项目
 </div>
 <button v-for="p in projects.projects" :key="p.id"
 @click="switchProject(p.id)"
 :class="['w-full text-left px-3 py-2 text-sm flex items-center gap-2 hover:bg-black/5 dark:hover:bg-white/10 dark:bg-white/10',
 selectedProjectId === p.id ? 'bg-apple-blue/10 font-semibold' : '']">
 <span class="w-3 h-3 rounded-full shrink-0" :style="{ background: p.color }"></span>
 <span class="flex-1 truncate">{{ p.name }}</span>
 <span v-if="selectedProjectId === p.id" class="text-apple-blue text-xs">✓</span>
 </button>
 <div v-if="projects.projects.length > 0" class="border-t border-black/5 dark:border-white/10 my-1"></div>
 <button @click="openProjectPanel"
 class="w-full text-left px-3 py-2 text-sm hover:bg-black/5 dark:hover:bg-white/10 dark:bg-white/10 text-gray-600">
 ⚙ 项目设置...
 </button>
 </div>
 </Teleport>
 <button @click="openNewProject"
 class="px-3 py-1.5 rounded-lg bg-apple-blue text-white text-sm font-semibold">
 + 新建项目
 </button>
 <button @click="addTask"
 class="px-3 py-1.5 rounded-lg bg-black/5 dark:bg-white/10 text-sm font-semibold">
 + 添加任务
 </button>
 </div>
 <div class="flex items-center gap-2">
 <button v-if="currentProject" @click="exportCurrent"
         class="px-3 py-1.5 rounded-lg bg-apple-blue/10 text-apple-blue text-sm font-semibold hover:bg-apple-blue/15"
         title="导出 Excel (4 个 Sheet + 甘特图 PNG)">
   📥 导出
 </button>
 <button @click="goToday" class="px-3 py-1.5 rounded-lg bg-apple-blue/10 text-apple-blue text-sm font-semibold">今天</button>
 <div class="flex gap-1 p-1 bg-black/5 dark:bg-white/10 rounded-lg">
 <button v-for="z in zooms" :key="z"
 @click="setZoom(z)"
 :class="['px-3 py-1 text-xs rounded-md',
 zoom === z ? 'bg-white shadow font-semibold' : 'text-gray-500 dark:text-gray-400']">
 {{ z }}
 </button>
 </div>
 </div>
 </div>

 <div v-if="!selectedProjectId" class="text-center py-16 text-gray-500 dark:text-gray-400">
 还没有项目，点击"新建项目"开始
 </div>

 <div v-else class="flex rounded-xl overflow-hidden border border-black/5 dark:border-white/10">
 <!-- 左侧任务列表 -->
 <div class="w-72 shrink-0 bg-white/40 dark:bg-white/[0.04] border-r border-black/5 dark:border-white/10 max-h-[520px] overflow-y-auto">
 <div v-for="t in orderedTasks" :key="t.id"
 class="flex items-center gap-2 px-3 py-2.5 border-b border-black/5 dark:border-white/10 text-sm cursor-pointer hover:bg-white/60 dark:bg-white/10"
 :style="{ paddingLeft: indentOf(t) + 'px' }"
 @click="openDetail(t.id)">
 <span class="flex-1 truncate" :class="{ 'font-bold': !t.parent_id }">{{ t.name }}</span>
 <StatusBadge :status="t.status" />
 </div>
 <div v-if="orderedTasks.length === 0" class="p-6 text-center text-sm text-gray-400 dark:text-gray-500">
 暂无任务，点击"添加任务"
 </div>
 </div>

 <!-- 右侧日历/时间轴 -->
 <div class="flex-1 bg-white/20 dark:bg-white/[0.03] min-w-0">
 <div class="flex items-center justify-between px-4 h-10 border-b border-black/5 dark:border-white/10">
 <div class="flex items-center gap-2 text-sm">
 <button @click="prev" class="w-7 h-7 rounded-md bg-black/5 dark:bg-white/10 hover:bg-black/10 dark:hover:bg-white/10 dark:bg-white/10 text-gray-600">‹</button>
 <span class="font-semibold w-32 text-center">{{ headerLabel }}</span>
 <button @click="next" class="w-7 h-7 rounded-md bg-black/5 dark:bg-white/10 hover:bg-black/10 dark:hover:bg-white/10 dark:bg-white/10 text-gray-600">›</button>
 <button @click="goToday" class="ml-1 px-2 py-0.5 rounded-md bg-apple-blue/10 text-apple-blue text-xs font-semibold">回到{{ zoom === '月' ? '本月' : '今天' }}</button>
 </div>
 <span class="text-xs text-gray-500 dark:text-gray-400">{{ visibleTasks.length }} 任务</span>
 </div>

 <div v-if="orderedTasks.length === 0" class="text-center text-sm text-gray-400 dark:text-gray-500 py-16">
 暂无带日期的任务
 </div>

 <!-- 月：日历网格 -->
 <div v-else-if="zoom === '月'" class="px-3 py-3 overflow-auto max-h-[480px]">
 <div class="grid grid-cols-7 gap-1 text-center text-xs text-gray-500 dark:text-gray-400 mb-1">
 <div v-for="w in weekdays" :key="w">{{ w }}</div>
 </div>
 <div class="grid grid-cols-7 gap-1">
 <div v-for="d in monthCells" :key="d.key"
 class="min-h-[80px] rounded-lg border p-1"
 :class="[d.inMonth ? (d.isToday ? 'border-apple-blue bg-apple-blue/5' : 'border-black/5 dark:border-white/10 bg-white/40 dark:bg-white/[0.04]') : 'border-transparent bg-transparent opacity-30']">
 <div v-if="d.inMonth" class="text-[11px] font-semibold mb-1"
 :class="d.isToday ? 'text-apple-blue' : 'text-gray-500 dark:text-gray-400'">{{ d.day }}</div>
 <div v-if="d.inMonth" class="space-y-1">
 <div v-for="t in d.tasks" :key="t.id"
 @click="openDetail(t.id)"
 class="text-[10px] px-1 py-0.5 rounded bg-white/85 dark:bg-white/15 border border-black/5 dark:border-white/10 shadow-sm cursor-pointer truncate hover:bg-white"
 :title="t.name">
 <span class="inline-block w-1.5 h-1.5 rounded-full mr-1" :style="{ background: statusColor(t.status) }"></span>
 {{ t.name }}
 </div>
 </div>
 </div>
 </div>
 </div>

 <!-- 周：单行时间轴 -->
 <div v-else-if="zoom === '周'" class="px-3 py-3 overflow-auto max-h-[480px]">
 <div class="flex border-b border-black/5 dark:border-white/10 text-[10px] text-gray-500 dark:text-gray-400 mb-2">
 <div class="w-28 shrink-0"></div>
 <div class="flex-1 grid grid-cols-7 gap-0">
 <div v-for="d in weekDays" :key="d.iso"
 class="text-center py-1"
 :class="d.isToday ? 'text-apple-blue font-semibold' : ''">
 <div>{{ d.weekday }}</div>
 <div class="text-sm font-semibold text-gray-700 dark:text-gray-200">{{ d.day }}</div>
 </div>
 </div>
 </div>
 <div v-for="t in orderedTasks" :key="t.id"
 class="flex items-center text-xs h-8 border-b border-black/5 dark:border-white/10">
 <div class="w-28 shrink-0 truncate pr-2 cursor-pointer hover:text-apple-blue"
 @click="openDetail(t.id)">{{ t.name }}</div>
 <div class="flex-1 relative h-6">
 <div class="absolute inset-0 grid grid-cols-7 gap-0">
 <div v-for="d in weekDays" :key="d.iso"
 class="border-l border-black/5 dark:border-white/10 first:border-l-0"
 :class="d.isToday ? 'bg-apple-blue/5' : ''"></div>
 </div>
 <div v-if="weekBarOf(t).visible"
 class="absolute top-1 h-4 rounded-md shadow-sm flex items-center px-2 text-white text-[10px] font-semibold cursor-pointer hover:opacity-90"
 :style="{ left: weekBarOf(t).left + '%', width: weekBarOf(t).width + '%', background: statusColor(t.status) }"
 :title="`${t.name} · ${t.start_date} → ${t.end_date}`"
 @click="openDetail(t.id)">
 <span class="truncate">{{ t.name }}</span>
 </div>
 </div>
 </div>
 </div>

 <!-- 日：紧凑单行 -->
 <div v-else class="px-3 py-3 overflow-auto max-h-[480px]">
 <div class="flex border-b border-black/5 dark:border-white/10 text-[10px] text-gray-500 dark:text-gray-400 mb-2">
 <div class="w-28 shrink-0"></div>
 <div class="flex-1 grid grid-cols-1 gap-0">
 <div v-for="d in weekDays" :key="d.iso"
 class="text-center py-1"
 :class="d.isToday ? 'text-apple-blue font-semibold' : ''">
 <div>{{ d.weekday }}</div>
 <div class="text-sm font-semibold text-gray-700 dark:text-gray-200">{{ d.day }}</div>
 </div>
 </div>
 </div>
 <div v-for="t in orderedTasks" :key="t.id"
 class="flex items-center text-xs h-7 border-b border-black/5 dark:border-white/10">
 <div class="w-28 shrink-0 truncate pr-2 cursor-pointer hover:text-apple-blue"
 @click="openDetail(t.id)">{{ t.name }}</div>
 <div class="flex-1 relative h-5">
 <div class="absolute inset-0 grid grid-cols-1 gap-0">
 <div v-for="d in weekDays" :key="d.iso"
 class="border-l border-black/5 dark:border-white/10 first:border-l-0"
 :class="d.isToday ? 'bg-apple-blue/5' : ''"></div>
 </div>
 <div v-if="weekBarOf(t).visible"
 class="absolute top-0.5 h-3.5 rounded-md shadow-sm flex items-center px-1.5 text-white text-[10px] font-semibold cursor-pointer hover:opacity-90"
 :style="{ left: weekBarOf(t).left + '%', width: weekBarOf(t).width + '%', background: statusColor(t.status) }"
 :title="`${t.name} · ${t.start_date} → ${t.end_date}`"
 @click="openDetail(t.id)">
 <span class="truncate">{{ t.name }}</span>
 </div>
 </div>
 </div>
 </div>
 </div>
 </div>

 <!-- 新建任务对话框 -->
 <Teleport to="body">
 <div v-if="showNewTask"
 class="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50"
 @click.self="showNewTask = false">
 <GlassCard class="p-6 w-[420px]">
 <h3 class="text-lg font-bold mb-4">添加任务</h3>
 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">任务名</label>
 <input v-model="newTask.name" placeholder="任务名" @keyup.enter="confirmNewTask"
 class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 mb-3 bg-white/70 dark:bg-white/15" />
 <div class="grid grid-cols-2 gap-3 mb-3">
 <div>
 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">开始日期</label>
 <input v-model="newTask.start_date" type="date"
 class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 bg-white/70 dark:bg-white/15" />
 </div>
 <div>
 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">结束日期</label>
 <input v-model="newTask.end_date" type="date"
 class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 bg-white/70 dark:bg-white/15" />
 </div>
 </div>
 <div class="flex gap-2 justify-end">
 <button @click="showNewTask = false" class="px-3 py-1.5 rounded-lg bg-black/5 dark:bg-white/10">取消</button>
 <button @click="confirmNewTask" class="px-3 py-1.5 rounded-lg bg-apple-blue text-white font-semibold">创建</button>
 </div>
 </GlassCard>
 </div>
 </Teleport>

 <ProjectPanel :open="showProjectPanel" :project="panelProject"
 @close="showProjectPanel = false"
 @saved="onPanelSaved"
 @deleted="onPanelDeleted" />
 </GlassCard>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { format, addDays, addWeeks, addMonths, startOfWeek, startOfMonth, isSameDay } from 'date-fns'
import GlassCard from '@/components/GlassCard.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import ProjectPanel from '@/components/ProjectPanel.vue'
import { useProjectsStore } from '@/stores/projects'
import { useTasksStore } from '@/stores/tasks'
import { projectsApi } from '@/api/client'
import type { Task, Project, TaskStatus } from '@/api/types'

const router = useRouter()
const projects = useProjectsStore()
const tasksStore = useTasksStore()

const zooms = ['日', '周', '月'] as const
type Zoom = (typeof zooms)[number]
const zoom = ref<Zoom>('月')

const showNewTask = ref(false)
const newTask = ref({ name: '', start_date: '', end_date: '' })
const projectMenuOpen = ref(false)
const projectMenuRef = ref<HTMLElement | null>(null)
const projectMenuTrigger = ref<HTMLElement | null>(null)
const projectMenuPosition = ref({ top: '0px', left: '0px' })

function toggleProjectMenu() {
 if (projectMenuOpen.value) {
 projectMenuOpen.value = false
 return
 }
 const el = (projectMenuTrigger.value as any)?.$el ?? projectMenuTrigger.value
 if (el) {
 const rect = el.getBoundingClientRect()
 projectMenuPosition.value = {
 top: `${rect.bottom + 4}px`,
 left: `${rect.left}px`
 }
 }
 projectMenuOpen.value = true
}

function switchProject(id: number) {
 selectedProjectId.value = id
 projectMenuOpen.value = false
}

function handleProjectMenuClickOutside(e: MouseEvent) {
 if (!projectMenuOpen.value) return
 const target = e.target as Node
 if (projectMenuRef.value && projectMenuRef.value.contains(target)) return
 const trigger = (projectMenuTrigger.value as any)?.$el ?? projectMenuTrigger.value
 if (trigger && trigger.contains(target)) return
 projectMenuOpen.value = false
}

onMounted(() => document.addEventListener('click', handleProjectMenuClickOutside))
onUnmounted(() => document.removeEventListener('click', handleProjectMenuClickOutside))

const selectedProjectId = computed<number | null>({
 get: () => projects.currentId,
 set: (v) => { if (v !== null) projects.select(v) }
})

const currentProject = computed(() =>
 projects.projects.find(p => p.id === selectedProjectId.value) ?? null
)

const showProjectPanel = ref(false)
const panelProject = ref<Project | null>(null)

function openProjectPanel() {
 panelProject.value = currentProject.value
 showProjectPanel.value = true
}
function openNewProject() {
 panelProject.value = null
 showProjectPanel.value = true
}

async function exportCurrent() {
 const p = currentProject.value
 if (!p) return
 try {
   await projectsApi.export(p.id, p.name)
 } catch {
   // axios interceptor 已提示
 }
}
async function onPanelSaved(p: Project) {
 showProjectPanel.value = false
 await projects.fetchAll()
 selectedProjectId.value = p.id
 await onProjectChange()
}
async function onPanelDeleted() {
 showProjectPanel.value = false
 await projects.fetchAll()
 if (projects.projects.length > 0) {
 selectedProjectId.value = projects.projects[0].id
 await onProjectChange()
 } else {
 selectedProjectId.value = null
 }
}

const orderedTasks = computed(() => {
 const byParent = new Map<number | null, Task[]>()
 for (const t of tasksStore.tasks) {
 const k = t.parent_id
 if (!byParent.has(k)) byParent.set(k, [])
 byParent.get(k)!.push(t)
 }
 for (const arr of byParent.values()) {
 arr.sort((a, b) => a.sort_order - b.sort_order || a.id - b.id)
 }
 const out: Task[] = []
 const visit = (parentId: number | null) => {
 for (const t of byParent.get(parentId) ?? []) {
 out.push(t)
 visit(t.id)
 }
 }
 visit(null)
 return out
})

const visibleTasks = computed(() => orderedTasks.value)

function indentOf(t: Task): number {
 let depth = 0
 let cur = t
 while (cur.parent_id !== null && depth < 5) {
 const parent = tasksStore.byId.get(cur.parent_id)
 if (!parent) break
 cur = parent
 depth++
 }
 return 12 + depth * 16
}

function openDetail(taskId: number) {
 if (selectedProjectId.value === null) return
 router.push(`/gantt/${selectedProjectId.value}/task/${taskId}`)
}

async function onProjectChange() {
 if (projects.currentId === null) return
 const targetId = projects.currentId
 await tasksStore.fetchByProject(targetId)
 if (projects.currentId !== targetId) return
 cursor.value = new Date()
}

const cursor = ref(new Date())

function setZoom(z: Zoom) {
 zoom.value = z
 if (z === '月') cursor.value = startOfMonth(cursor.value)
 else if (z === '周') cursor.value = startOfWeek(cursor.value, { weekStartsOn: 0 })
}

function goToday() {
 if (zoom.value === '月') cursor.value = startOfMonth(new Date())
 else if (zoom.value === '周') cursor.value = startOfWeek(new Date(), { weekStartsOn: 0 })
 else cursor.value = new Date()
}

function shiftCursor(delta: number) {
 if (zoom.value === '月') cursor.value = addMonths(cursor.value, delta)
 else if (zoom.value === '周') cursor.value = addWeeks(cursor.value, delta)
 else cursor.value = addDays(cursor.value, delta)
}
function prev() { shiftCursor(-1) }
function next() { shiftCursor(1) }

const weekdays = ['日', '一', '二', '三', '四', '五', '六']

const statusColorMap: Record<TaskStatus, string> = {
 todo: '#8e8e93', progress: '#0071e3', delayed: '#ff9500',
 done: '#34c759', cancelled: '#af52de'
}
function statusColor(s: TaskStatus) { return statusColorMap[s] ?? '#8e8e93' }

interface MonthCell {
 key: string
 day: number
 inMonth: boolean
 isToday: boolean
 tasks: Task[]
}

const monthCells = computed<MonthCell[]>(() => {
 const y = cursor.value.getFullYear()
 const m = cursor.value.getMonth()
 const first = new Date(y, m, 1)
 const daysInMonth = new Date(y, m + 1, 0).getDate()
 const lead = first.getDay()
 const today = new Date()
 const totalCells = Math.ceil((lead + daysInMonth) / 7) * 7
 const cells: MonthCell[] = []
 for (let i = 0; i < totalCells; i++) {
 const dayNum = i - lead + 1
 const inMonth = dayNum >= 1 && dayNum <= daysInMonth
 const d = new Date(y, m, dayNum)
 const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
 const isToday = isSameDay(d, today)
 const dayTasks: Task[] = []
if (inMonth) {
     for (const t of visibleTasks.value) {
     if (!t.start_date) continue
     const start = new Date(t.start_date + 'T00:00:00')
     const end = t.end_date ? new Date(t.end_date + 'T00:00:00') : start
     if (t.status === 'cancelled') continue
     const inRange = d >= start && d <= end
 const isDue = d.getTime() === end.getTime()
 if (inRange || isDue) dayTasks.push(t)
 }
 }
 cells.push({ key, day: dayNum, inMonth, isToday, tasks: dayTasks })
 }
 return cells
})

const weekDays = computed(() => {
 const today = new Date()
 if (zoom.value === '日') {
 const d = new Date(cursor.value)
 return [{
 iso: format(d, 'yyyy-MM-dd'),
 day: d.getDate(),
 weekday: weekdays[d.getDay()],
 isToday: isSameDay(d, today)
 }]
 }
 const start = startOfWeek(cursor.value, { weekStartsOn: 0 })
 return Array.from({ length: 7 }, (_, i) => {
 const d = addDays(start, i)
 return {
 iso: format(d, 'yyyy-MM-dd'),
 day: d.getDate(),
 weekday: weekdays[d.getDay()],
 isToday: isSameDay(d, today)
 }
 })
})

const headerLabel = computed(() => {
 if (zoom.value === '月') {
 return `${cursor.value.getFullYear()}年${cursor.value.getMonth() + 1}月`
 }
 const s = weekDays.value[0]
 const e = weekDays.value[weekDays.value.length - 1]
 if (s.iso === e.iso) {
 return `${s.iso} · 周${s.weekday}`
 }
 if (s.iso.slice(0, 7) === e.iso.slice(0, 7)) {
 return `${s.iso.slice(0, 4)}-${s.iso.slice(5, 7)} · ${s.day}–${e.day}`
 }
 return `${s.iso} → ${e.iso}`
})

function weekBarOf(t: Task): { visible: boolean; left: number; width: number } {
 if (!t.start_date) return { visible: false, left: 0, width: 0 }
 const startStr = t.start_date
 const endStr = t.end_date ?? t.start_date
 const startD = new Date(startStr + 'T00:00:00')
 const endD = new Date(endStr + 'T00:00:00')
 const w0 = new Date(weekDays.value[0].iso + 'T00:00:00')
 const wN = new Date(weekDays.value[weekDays.value.length - 1].iso + 'T00:00:00')
 if (endD < w0 || startD > wN) return { visible: false, left: 0, width: 0 }
 const total = weekDays.value.length
 const dayMs = 24 * 60 * 60 * 1000
 const clampStart = startD < w0 ? w0 : startD
 const clampEnd = endD > wN ? wN : endD
 const startOffset = Math.round((clampStart.getTime() - w0.getTime()) / dayMs)
 const endOffset = Math.round((clampEnd.getTime() - w0.getTime()) / dayMs) + 1
 const left = (startOffset / total) * 100
 const width = Math.max(((endOffset - startOffset) / total) * 100, 4)
 return { visible: true, left, width }
}

async function addTask() {
 if (!selectedProjectId.value) return
 const now = new Date()
 newTask.value = {
 name: '',
 start_date: format(now, 'yyyy-MM-dd'),
 end_date: format(addDays(now, 7), 'yyyy-MM-dd')
 }
 showNewTask.value = true
}

async function confirmNewTask() {
 if (!newTask.value.name.trim() || !selectedProjectId.value) return
 await tasksStore.create(selectedProjectId.value, {
 name: newTask.value.name.trim(),
 start_date: newTask.value.start_date || null,
 end_date: newTask.value.end_date || null
 })
 newTask.value = { name: '', start_date: '', end_date: '' }
 showNewTask.value = false
}

watch(() => projects.currentId, () => {
 onProjectChange()
})

onMounted(async () => {
 if (projects.currentId === null && projects.projects.length === 0) {
 await projects.fetchAll()
 }
 if (projects.currentId !== null) {
 await tasksStore.fetchByProject(projects.currentId)
 }
})
</script>
