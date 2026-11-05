<template>
 <div class="space-y-5">
 <!-- KPI 行 -->
 <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
 <GlassCard class="p-4">
 <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">📁 项目数</div>
 <div class="text-3xl font-bold">{{ overview?.project_count ?? 0 }}</div>
 </GlassCard>
 <GlassCard class="p-4">
 <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">🔵 进行中任务</div>
 <div class="text-3xl font-bold text-apple-blue">{{ overview?.active_task_count ?? 0 }}</div>
 </GlassCard>
 <GlassCard class="p-4">
 <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">⚠️ 延期任务</div>
 <div class="text-3xl font-bold text-apple-orange">{{ overview?.delayed_task_count ?? 0 }}</div>
 </GlassCard>
 <GlassCard class="p-4">
 <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">💰 本月支出</div>
 <div class="text-3xl font-bold">¥{{ (overview?.this_month_cost ?? 0).toFixed(2) }}</div>
 </GlassCard>
 </div>

 <!-- 月度日历 -->
 <GlassCard class="p-5">
 <div class="flex items-center justify-between mb-4">
 <h2 class="text-lg font-bold">📅 月度任务日历</h2>
 <div class="flex items-center gap-2">
 <button @click="prevMonth" class="px-3 py-1 rounded-lg bg-black/5 dark:bg-white/10 hover:bg-black/10 dark:hover:bg-white/10 dark:bg-white/10 text-sm font-medium">◀</button>
 <span class="text-sm font-semibold w-28 text-center">{{ monthLabel }}</span>
 <button @click="nextMonth" class="px-3 py-1 rounded-lg bg-black/5 dark:bg-white/10 hover:bg-black/10 dark:hover:bg-white/10 dark:bg-white/10 text-sm font-medium">▶</button>
 <button @click="goToday" class="px-3 py-1 rounded-lg bg-apple-blue/10 text-apple-blue text-sm font-medium">回到本月</button>
 </div>
 </div>
 <div class="grid grid-cols-7 gap-1 text-center text-xs text-gray-500 dark:text-gray-400 mb-1">
 <div v-for="w in weekdays" :key="w">{{ w }}</div>
 </div>
 <div class="grid grid-cols-7 gap-1">
 <div v-for="d in calendarCells" :key="d.key"
 class="min-h-[88px] rounded-lg border p-1.5"
 :class="[d.isToday ? 'border-apple-blue bg-apple-blue/5' : 'border-black/5 dark:border-white/10 bg-white/40 dark:bg-white/[0.04]', d.inMonth ? '' : 'opacity-30']">
 <div class="text-xs font-semibold" :class="{ 'text-apple-blue': d.isToday }">{{ d.day }}</div>
 <div class="mt-1 space-y-1">
 <div v-for="t in d.tasks" :key="t.id"
 @click="openTask(t.id)"
 class="text-[11px] px-1 py-0.5 rounded bg-white/80 shadow-sm cursor-pointer truncate hover:bg-white"
 :title="t.projectName + ' · ' + t.name">
 <span class="inline-block w-1.5 h-1.5 rounded-full mr-1" :style="{ background: statusColor(t.status) }"></span>
 {{ t.projectName }}·{{ t.name }}
 </div>
 </div>
 </div>
 </div>
 </GlassCard>

 <!-- 项目进度 -->
 <GlassCard class="p-5">
 <h2 class="text-lg font-bold mb-4">📁 项目进度</h2>
 <div v-if="overview && overview.projects.length === 0" class="text-sm text-gray-400 dark:text-gray-500 text-center py-8">
 还没有项目，去创建第一个吧
 </div>
 <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
 <div v-for="p in overview?.projects ?? []" :key="p.id"
 @click="goProject(p.id)"
 class="p-4 rounded-xl bg-white/50 dark:bg-white/10 border border-black/5 dark:border-white/10 cursor-pointer hover:bg-white/80 transition">
 <div class="flex items-center gap-2 mb-2">
 <span class="w-3 h-3 rounded-full" :style="{ background: p.color }"></span>
 <span class="font-semibold">{{ p.name }}</span>
 <span class="ml-auto text-xs text-gray-500 dark:text-gray-400">{{ p.task_done }}/{{ p.task_total }} 完成</span>
 </div>
 <div class="h-2 bg-black/5 dark:bg-white/10 rounded-full overflow-hidden mb-2">
 <div class="h-full bg-gradient-to-r from-sky-400 to-apple-blue"
 :style="{ width: p.progress + '%' }"></div>
 </div>
 <div class="text-xs text-gray-500 dark:text-gray-400">
 {{ p.progress }}%
 <span v-if="p.next_due_task" class="ml-2">⏰ 下个截止：{{ p.next_due_task.name }}（{{ p.next_due_task.end_date }}）</span>
 </div>
 </div>
 </div>
 </GlassCard>

 <!-- 月度费用趋势 -->
 <GlassCard class="p-5">
 <h2 class="text-lg font-bold mb-4">💰 月度费用趋势</h2>
 <div v-if="monthBars.length === 0" class="text-sm text-gray-400 dark:text-gray-500 text-center py-8">暂无费用数据</div>
 <div v-else class="flex items-end gap-2 h-40 px-2">
 <div v-for="m in monthBars" :key="m.key" class="flex-1 flex flex-col items-center gap-1">
 <div class="w-full max-w-[40px] rounded-t-md bg-apple-blue"
 :style="{ height: barHeight(m.total) + 'px' }"
 :title="`${m.label}: ¥${m.total.toFixed(2)}`"></div>
 <div class="text-[10px] text-gray-500 dark:text-gray-400">{{ m.short }}</div>
 </div>
 </div>
 </GlassCard>
 </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import GlassCard from '@/components/GlassCard.vue'
import { statsApi, costsApi } from '@/api/client'
import type { Overview } from '@/api/client'
import { useProjectsStore } from '@/stores/projects'
import { useTasksStore } from '@/stores/tasks'
import type { CostStats, TaskStatus } from '@/api/types'

const router = useRouter()
const projects = useProjectsStore()
const tasksStore = useTasksStore()

const overview = ref<Overview | null>(null)
const costStats = ref<CostStats>({ total: 0, count: 0, by_category: {}, by_month: {} })

const viewMonth = ref(new Date())
const weekdays = ['日', '一', '二', '三', '四', '五', '六']

const statusColorMap: Record<TaskStatus, string> = {
 todo: '#8e8e93', progress: '#0071e3', delayed: '#ff9500',
 done: '#34c759', cancelled: '#af52de'
}
function statusColor(s: TaskStatus) { return statusColorMap[s] ?? '#8e8e93' }

const monthLabel = computed(() => {
 const d = viewMonth.value
 return `${d.getFullYear()}年${d.getMonth() + 1}月`
})

interface CellTask { id: number; name: string; projectName: string; status: TaskStatus }
interface CalendarCell {
 key: string; day: number; inMonth: boolean; isToday: boolean; tasks: CellTask[]
}

const calendarCells = computed<CalendarCell[]>(() => {
 const y = viewMonth.value.getFullYear()
 const m = viewMonth.value.getMonth()
 const first = new Date(y, m, 1)
 const daysInMonth = new Date(y, m + 1, 0).getDate()
 const lead = first.getDay()
 const today = new Date()
 const todayKey = `${today.getFullYear()}-${today.getMonth()}-${today.getDate()}`

 const allTasks = tasksStore.tasks.map(t => {
 const p = projects.byId.get(t.project_id)
 return { ...t, projectName: p?.name ?? `#${t.project_id}` }
 })

 const cells: CalendarCell[] = []
 const totalCells = Math.ceil((lead + daysInMonth) / 7) * 7
 for (let i = 0; i < totalCells; i++) {
 const dayNum = i - lead + 1
 const inMonth = dayNum >= 1 && dayNum <= daysInMonth
 const d = new Date(y, m, dayNum)
 const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
 const isToday = key === todayKey
 const dayTasks: CellTask[] = []
 if (inMonth) {
 for (const t of allTasks) {
 if (!t.start_date) continue
 const start = new Date(t.start_date + 'T00:00:00')
 const end = t.end_date ? new Date(t.end_date + 'T00:00:00') : start
 if (t.status === 'cancelled') continue
 const inRange = d >= start && d <= end
 const isDue = d.getTime() === end.getTime()
 if (inRange || isDue) {
 dayTasks.push({ id: t.id, name: t.name, projectName: t.projectName, status: t.status })
 }
 }
 }
 cells.push({ key, day: dayNum, inMonth, isToday, tasks: dayTasks })
 }
 return cells
})

function prevMonth() { viewMonth.value = new Date(viewMonth.value.getFullYear(), viewMonth.value.getMonth() - 1, 1) }
function nextMonth() { viewMonth.value = new Date(viewMonth.value.getFullYear(), viewMonth.value.getMonth() + 1, 1) }
function goToday() { viewMonth.value = new Date() }

function openTask(taskId: number) {
 const t = tasksStore.tasks.find(x => x.id === taskId)
 if (t) router.push(`/gantt/${t.project_id}/task/${taskId}`)
}

function goProject(projectId: number) {
 projects.select(projectId)
 router.push('/gantt')
}

const monthBars = computed(() => {
 const months = Object.entries(costStats.value.by_month)
 .sort(([a], [b]) => a.localeCompare(b))
 .slice(-12)
 .map(([key, total]) => ({ key, total, short: key.slice(2).replace('-', '/'), label: key }))
 return months
})

const maxMonth = computed(() => Math.max(...monthBars.value.map(m => m.total), 1))
function barHeight(total: number) { return Math.max(2, Math.round((total / maxMonth.value) * 100)) }

onMounted(async () => {
 if (projects.projects.length === 0) await projects.fetchAll()
 await Promise.all([
 tasksStore.fetchAll(),
 statsApi.overview().then(d => { overview.value = d }),
 costsApi.stats().then(d => { costStats.value = d })
 ])
})
</script>