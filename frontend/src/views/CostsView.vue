<template>
 <div class="space-y-5">
 <GlassCard class="p-5">
 <div class="flex items-center justify-between mb-4">
 <div>
 <h2 class="text-xl font-bold">💰 费用记录</h2>
 <p class="text-sm text-gray-500 dark:text-gray-400">记录每一笔支出，按项目 / 类别 / 月份统计</p>
 </div>
 <div class="flex items-center gap-2">
 <button @click="router.push('/settings')"
 class="px-3 py-1.5 rounded-lg bg-black/5 dark:bg-white/10 text-sm font-medium hover:bg-black/10 dark:hover:bg-white/10 dark:bg-white/10">
 ⚙ 类别
 </button>
 <button @click="exportCurrentProject"
 class="px-3 py-1.5 rounded-lg bg-apple-blue/10 text-apple-blue text-sm font-semibold hover:bg-apple-blue/15"
 title="导出当前选中项目（含任务表 + 甘特图 PNG）">
 📥 导出
 </button>
 <button @click="openCreate"
 class="px-3 py-1.5 rounded-lg bg-apple-blue text-white text-sm font-semibold">
 + 记一笔
 </button>
 </div>
 </div>

 <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
 <div class="p-4 bg-black/[0.03] dark:bg-white/[0.04] rounded-xl">
 <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">总支出</div>
 <div class="text-2xl font-bold">¥{{ stats.total.toFixed(2) }}</div>
 </div>
 <div class="p-4 bg-black/[0.03] dark:bg-white/[0.04] rounded-xl">
 <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">笔数</div>
 <div class="text-2xl font-bold">{{ stats.count }}</div>
 </div>
 <div class="p-4 bg-black/[0.03] dark:bg-white/[0.04] rounded-xl">
 <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">本月</div>
 <div class="text-2xl font-bold">¥{{ currentMonthTotal.toFixed(2) }}</div>
 </div>
 <div class="p-4 bg-black/[0.03] dark:bg-white/[0.04] rounded-xl">
 <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">单笔最高</div>
 <div class="text-2xl font-bold">¥{{ maxAmount.toFixed(2) }}</div>
 </div>
 </div>

 <div class="flex gap-2 mb-5">
 <button @click="filterProject = null"
 :class="chipCls(filterProject === null)">全部项目</button>
 <button v-for="p in projects.projects" :key="p.id"
 @click="filterProject = p.id"
 :class="chipCls(filterProject === p.id)">
 {{ p.name }}
 </button>
 </div>

 <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
 <div class="bg-black/[0.02] dark:bg-white/[0.03] rounded-xl p-4">
 <h3 class="text-sm font-semibold mb-3">类别占比</h3>
 <div class="flex items-center gap-6">
 <div class="w-32 h-32 shrink-0 rounded-full relative"
 :style="{ background: pieBackground }">
 <div class="absolute inset-0 rounded-full bg-white/10 dark:bg-white/[0.04] flex flex-col items-center justify-center">
 <span class="text-lg font-bold">¥{{ stats.total.toFixed(0) }}</span>
 <span class="text-[10px] text-gray-500 dark:text-gray-400">总额</span>
 </div>
 </div>
 <div class="flex-1 space-y-2">
 <div v-for="c in categoryList" :key="c.key" class="flex items-center gap-2 text-sm">
 <span class="w-3 h-3 rounded-sm" :style="{ background: c.color }"></span>
 <span class="flex-1">{{ c.label }}</span>
 <span class="font-semibold">¥{{ c.total.toFixed(2) }}</span>
 <span class="text-gray-400 dark:text-gray-500 text-xs w-10 text-right">{{ c.pct }}%</span>
 </div>
 </div>
 </div>
 </div>

 <div class="bg-black/[0.02] dark:bg-white/[0.03] rounded-xl p-4">
 <div class="flex items-center justify-between mb-3">
 <h3 class="text-sm font-semibold">趋势</h3>
 <div class="flex gap-1">
 <button v-for="g in trendOptions" :key="g.key"
 @click="trendGranularity = g.key"
 :class="chipCls(trendGranularity === g.key)">{{ g.label }}</button>
 </div>
 </div>
 <div class="flex items-end gap-2 h-32 px-2 overflow-x-auto scrollbar-thin">
  <div v-for="b in trendList" :key="b.key" class="flex-none w-10 flex flex-col items-center gap-1">
 <div class="text-[10px] font-medium text-gray-700 dark:text-gray-300 leading-tight whitespace-nowrap">{{ fmtTrendAmount(b.total) }}</div>
 <div class="w-full max-w-[36px] rounded-t-md"
 :style="{ height: trendBarHeight(b.total) + 'px', background: '#0071e3' }"
 :title="`${b.label}: ¥${b.total.toFixed(2)}`"></div>
 <div class="text-[10px] text-gray-500 dark:text-gray-400">{{ b.short }}</div>
 </div>
 </div>
 <div v-if="trendList.length === 0" class="text-center text-sm text-gray-400 dark:text-gray-500 py-6">
 暂无趋势数据
 </div>
 </div>
 </div>
 </GlassCard>

 <GlassCard class="p-5">
 <div class="flex items-center justify-between mb-3">
 <h3 class="text-sm font-semibold">支出明细</h3>
 <span class="text-xs text-gray-500 dark:text-gray-400">{{ filteredCosts.length }} 笔</span>
 </div>
 <div v-if="filteredCosts.length === 0" class="text-center text-sm text-gray-400 dark:text-gray-500 py-10">
 还没有支出记录，点击右上角"记一笔"
 </div>
 <div v-else class="overflow-x-auto">
 <table class="w-full text-sm">
 <thead>
 <tr class="text-left text-xs text-gray-500 dark:text-gray-400 border-b border-black/5 dark:border-white/10">
 <th class="py-2 pr-3">日期</th>
 <th class="py-2 pr-3">名称</th>
 <th class="py-2 pr-3">类别</th>
 <th class="py-2 pr-3">说明</th>
 <th class="py-2 pr-3">项目</th>
 <th class="py-2 pr-3">任务</th>
 <th class="py-2 pr-3">附件</th>
 <th class="py-2 text-right">金额</th>
 <th class="py-2 w-16"></th>
 </tr>
 </thead>
 <tbody>
 <tr v-for="c in filteredCosts" :key="c.id" class="border-b border-black/5 dark:border-white/10">
 <td class="py-2.5 pr-3 text-gray-500 dark:text-gray-400">{{ c.spent_at }}</td>
 <td class="py-2.5 pr-3 min-w-36">
 <EditableName
 :model-value="c.name"
 text-class="font-medium"
 input-class="w-full min-w-0"
 :save="name => saveCostName(c.id, name)"
 />
 </td>
 <td class="py-2.5 pr-3">
 <span class="text-xs px-2 py-0.5 rounded-md font-semibold"
 :style="{ background: catColor(c.category) + '22', color: catColor(c.category) }">
 {{ catLabel(c.category) }}
 </span>
 </td>
 <td class="py-2.5 pr-3">{{ c.description || '—' }}</td>
 <td class="py-2.5 pr-3 text-gray-500 dark:text-gray-400">{{ projectName(c.project_id) }}</td>
 <td class="py-2.5 pr-3 text-gray-500 dark:text-gray-400">{{ taskName(c.task_id) }}</td>
 <td class="py-2.5 pr-3">
 <div v-if="(attachmentsByCost.get(c.id) ?? []).length > 0" class="flex items-center gap-1 flex-wrap">
 <a v-for="a in attachmentsByCost.get(c.id) ?? []" :key="a.id"
 :href="attachmentsApi.downloadUrl(a.id)" target="_blank" rel="noopener"
 :title="`${a.original_name} (${formatSize(a.size)})`"
 class="inline-flex items-center justify-center w-6 h-6 rounded-md bg-apple-blue/10 text-apple-blue hover:bg-apple-blue/20 text-xs">
 📎
 </a>
 </div>
 <span v-else class="text-gray-300 dark:text-gray-600 text-xs">—</span>
 </td>
 <td class="py-2.5 text-right font-semibold">¥{{ c.amount.toFixed(2) }}</td>
 <td class="py-2.5 text-right whitespace-nowrap">
 <button @click="openEdit(c)"
 class="text-xs text-apple-blue hover:underline mr-2">编辑</button>
 <button @click="removeCost(c.id)"
 class="text-xs text-red-500 hover:underline">删除</button>
 </td>
 </tr>
 </tbody>
 </table>
 </div>
 </GlassCard>

 <Teleport to="body">
 <div v-if="showForm"
 class="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50 p-4"
 @click.self="closeForm">
 <GlassCard class="p-6 w-[400px] max-w-full">
 <h3 class="text-lg font-bold mb-4">{{ editingId ? '编辑支出' : '记一笔支出' }}</h3>
 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">项目</label>
 <select v-model="form.project_id" class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 mb-3 bg-white/70 dark:bg-white/15">
 <option v-for="p in projects.projects" :key="p.id" :value="p.id">{{ p.name }}</option>
 </select>
 <label for="cost-name" class="block text-xs text-gray-500 dark:text-gray-400 mb-1">名称</label>
 <input id="cost-name" v-model="form.name" required maxlength="200" placeholder="如：客厅瓷砖"
 class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 mb-3 bg-white/70 dark:bg-white/15" />
 <div class="grid grid-cols-2 gap-3 mb-3">
 <div>
 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">金额（元）</label>
 <input v-model.number="form.amount" type="number" min="0.01" step="0.01" placeholder="0.00"
 class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 bg-white/70 dark:bg-white/15" />
 </div>
 <div>
 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">日期</label>
 <input v-model="form.spent_at" type="date"
 class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 bg-white/70 dark:bg-white/15" />
 </div>
 </div>
 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">类别</label>
 <select v-model="form.category" class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 mb-3 bg-white/70 dark:bg-white/15">
 <option v-for="c in categories.list" :key="c.id" :value="c.name">{{ c.name }}</option>
 </select>
 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">关联任务（可选）</label>
 <select v-model="form.task_id" class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 mb-3 bg-white/70 dark:bg-white/15">
 <option :value="null">— 不关联任务 —</option>
 <option v-for="t in projectTasks" :key="t.id" :value="t.id">{{ t.name }}</option>
 </select>
 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">说明</label>
 <input v-model="form.description" placeholder="如：购买瓷砖" @keyup.enter="submitForm"
 class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 mb-4 bg-white/70 dark:bg-white/15" />
 <div v-if="editingId" class="mb-4 pt-3 border-t border-black/5 dark:border-white/10">
 <AttachmentList entity-type="cost" :entity-id="editingId" />
 </div>
 <div v-else class="mb-4 pt-3 border-t border-black/5 dark:border-white/10">
 <div class="flex items-center justify-between mb-2">
 <span class="text-xs text-gray-500 dark:text-gray-400">
 附件 ({{ pendingFiles.length }} / 5)，保存后自动上传
 </span>
 <label
 class="px-2.5 py-1 rounded-lg bg-black/5 dark:bg-white/10 hover:bg-black/10 dark:hover:bg-white/15 text-xs font-medium cursor-pointer transition-colors"
 :class="{ 'pointer-events-none opacity-50': pendingFiles.length >= 5 }">
 + 添加附件
 <input type="file" multiple class="hidden" :disabled="pendingFiles.length >= 5" @change="onPickFiles" />
 </label>
 </div>
 <div v-if="pendingFiles.length === 0" class="text-xs text-gray-400 dark:text-gray-500 italic py-1">
 可附收据照片等，暂不占空间，保存时才上传
 </div>
 <div v-else class="space-y-1.5">
 <div v-for="(f, i) in pendingFiles" :key="i"
 class="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-black/[0.03] dark:bg-white/[0.04] text-xs">
 <span class="shrink-0">📎</span>
 <span class="flex-1 min-w-0 truncate font-medium" :title="f.name">{{ f.name }}</span>
 <span class="text-gray-400 dark:text-gray-500 shrink-0">{{ formatSize(f.size) }}</span>
 <button @click="removePendingFile(i)"
 class="text-red-500 hover:underline shrink-0">移除</button>
 </div>
 </div>
 </div>
 <div class="flex gap-2 justify-end">
 <button @click="closeForm" class="px-3 py-1.5 rounded-lg bg-black/5 dark:bg-white/10">取消</button>
 <button @click="submitForm"
 :disabled="!form.name.trim() || form.amount <= 0"
 class="px-3 py-1.5 rounded-lg bg-apple-blue text-white font-semibold disabled:opacity-50 disabled:cursor-not-allowed">
 {{ editingId ? '保存修改' : '保存' }}
 </button>
 </div>
 </GlassCard>
 </div>
 </Teleport>
 </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import EditableName from '@/components/EditableName.vue'
import GlassCard from '@/components/GlassCard.vue'
import AttachmentList from '@/components/AttachmentList.vue'
import { attachmentsApi, costsApi, formatSize, projectsApi, type Attachment } from '@/api/client'
import { useProjectsStore } from '@/stores/projects'
import { useCategoriesStore } from '@/stores/categories'
import { useTasksStore } from '@/stores/tasks'
import type { Cost, CostStats } from '@/api/types'

const projects = useProjectsStore()
const categories = useCategoriesStore()
const tasksStore = useTasksStore()
const router = useRouter()
const costs = ref<Cost[]>([])
const stats = ref<CostStats>({ total: 0, count: 0, by_category: {}, by_month: {} })
const filterProject = ref<number | null>(null)
const attachmentsByCost = ref<Map<number, Attachment[]>>(new Map())

const showForm = ref(false)
const editingId = ref<number | null>(null)
const form = ref<{
 project_id: number
 name: string
 amount: number
 spent_at: string
 category: string
 task_id: number | null
 description: string
}>({
 project_id: 0, name: '', amount: 0, spent_at: '', category: '',
 task_id: null, description: ''
})

function catColor(cat: string) { return categories.colorOf(cat) }
function catLabel(cat: string) {
 return categories.list.find(c => c.name === cat)?.name ?? cat
}

function projectName(id: number) {
 return projects.projects.find(p => p.id === id)?.name ?? `#${id}`
}

function taskName(tid: number | null) {
 if (!tid) return '—'
 return tasksStore.byId.get(tid)?.name ?? `#${tid}`
}

function chipCls(active: boolean) {
 return `px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
 active ? 'bg-apple-blue text-white' : 'bg-black/5 dark:bg-white/10 hover:bg-black/10 dark:hover:bg-white/10 dark:bg-white/10'
 }`
}

const filteredCosts = computed(() =>
 filterProject.value === null
 ? costs.value
 : costs.value.filter(c => c.project_id === filterProject.value)
)

const currentMonthTotal = computed(() => {
 const now = new Date()
 const key = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
 return stats.value.by_month[key] ?? 0
})

const maxAmount = computed(() =>
 filteredCosts.value.reduce((m, c) => Math.max(m, c.amount), 0)
)

const categoryList = computed(() =>
 categories.list.map(c => ({
 key: c.name,
 label: c.name,
 color: c.color,
 total: stats.value.by_category[c.name] ?? 0,
 pct: stats.value.total > 0 ? Math.round(((stats.value.by_category[c.name] ?? 0) / stats.value.total) * 100) : 0
 })).filter(c => c.total > 0 || categories.list.length === 0)
)

const projectTasks = computed(() =>
 tasksStore.tasks
 .filter(t => t.project_id === form.value.project_id)
 .sort((a, b) => a.sort_order - b.sort_order)
)

watch(() => form.value.project_id, () => {
 form.value.task_id = null
})

const pieBackground = computed(() => {
 const list = categoryList.value.filter(c => c.total > 0)
 if (list.length === 0) return '#eee'
 let cursor = 0
 const stops = list.map(c => {
 const from = cursor
 cursor += (c.total / stats.value.total) * 360
 return `${c.color} ${from}deg ${cursor}deg`
 })
 return `conic-gradient(${stops.join(', ')})`
})

const trendGranularity = ref<'month' | 'week' | 'day'>('month')

const trendOptions = [
 { key: 'month' as const, label: '月' },
 { key: 'week' as const, label: '周' },
 { key: 'day' as const, label: '日' },
]

function startOfWeek(d: Date): Date {
 const x = new Date(d.getFullYear(), d.getMonth(), d.getDate())
 const day = (x.getDay() + 6) % 7
 x.setDate(x.getDate() - day)
 return x
}

const trendMap = computed(() => {
 const out: Record<string, number> = {}
 const pid = filterProject.value
 for (const c of costs.value) {
 if (pid !== null && c.project_id !== pid) continue
 const d = new Date(c.spent_at + 'T00:00:00')
 let key: string
 if (trendGranularity.value === 'month') {
 key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
 } else if (trendGranularity.value === 'week') {
 const m = startOfWeek(d)
 key = `${m.getFullYear()}-${String(m.getMonth() + 1).padStart(2, '0')}-${String(m.getDate()).padStart(2, '0')}`
 } else {
 key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
 }
 out[key] = (out[key] ?? 0) + c.amount
 }
 return out
})

const trendLimit = computed(() => trendGranularity.value === 'day' ? 30 : 12)

const trendList = computed(() => {
 const entries = Object.entries(trendMap.value).sort(([a], [b]) => a.localeCompare(b))
 return entries.slice(-trendLimit.value).map(([key, total]) => {
 const parts = key.split('-')
 const short = trendGranularity.value === 'month' ? parts[1] : `${parts[1]}/${parts[2]}`
 return { key, total, short, label: key }
 })
})

const trendMax = computed(() => Math.max(...trendList.value.map(b => b.total), 1))

function trendBarHeight(total: number) {
 return Math.max(2, Math.round((total / trendMax.value) * 100))
}

function fmtTrendAmount(n: number): string {
 return `¥${n.toFixed(2)}`
}

async function load() {
 if (projects.projects.length === 0) await projects.fetchAll()
 if (projects.currentId && tasksStore.tasks.filter(t => t.project_id === projects.currentId).length === 0) {
 await tasksStore.fetchByProject(projects.currentId)
 }
 const lists = await Promise.all(projects.projects.map(p => costsApi.listByProject(p.id)))
 costs.value = lists.flat()
 stats.value = await costsApi.stats(filterProject.value ?? undefined)
 await loadAttachments()
}

async function loadAttachments() {
 const map = new Map<number, Attachment[]>()
 await Promise.all(
 costs.value.map(async c => {
 try {
 const atts = await attachmentsApi.list('cost', c.id)
 if (atts.length > 0) map.set(c.id, atts)
 } catch {
 // ignore — list failures shouldn't block the cost list
 }
 })
 )
 attachmentsByCost.value = map
}

watch(filterProject, () => { load() })
watch(() => projects.currentId, () => { load() })
watch(() => projects.projects.length, () => { load() })

function openCreate() {
  const selectedId = filterProject.value ?? projects.currentId ?? projects.projects[0]?.id ?? 0
  form.value = {
  project_id: selectedId,
  name: '',
  amount: 0,
  spent_at: new Date().toISOString().slice(0, 10),
  category: categories.list[0]?.name ?? '',
  task_id: null,
  description: ''
  }
  editingId.value = null
  pendingFiles.value = []
  showForm.value = true
}

function openEdit(c: Cost) {
 form.value = {
 project_id: c.project_id,
 name: c.name,
 amount: c.amount,
 spent_at: c.spent_at,
 category: c.category,
 task_id: c.task_id ?? null,
 description: c.description ?? ''
 }
 editingId.value = c.id
 if (c.project_id && tasksStore.tasks.filter(t => t.project_id === c.project_id).length === 0) {
 tasksStore.fetchByProject(c.project_id)
 }
 showForm.value = true
}

function closeForm() {
  showForm.value = false
  editingId.value = null
  pendingFiles.value = []
}

const pendingFiles = ref<File[]>([])
const COST_ATTACHMENT_LIMIT = 5
const MAX_FILE_BYTES = 20 * 1024 * 1024

function onPickFiles(e: Event) {
  const target = e.target as HTMLInputElement
  const files = Array.from(target.files ?? [])
  for (const f of files) {
    if (pendingFiles.value.length >= COST_ATTACHMENT_LIMIT) break
    if (f.size > MAX_FILE_BYTES) {
      window.alert(`「${f.name}」超过 20 MB 上限，已跳过`)
      continue
    }
    pendingFiles.value.push(f)
  }
  target.value = ''
}

function removePendingFile(index: number) {
  pendingFiles.value.splice(index, 1)
}

async function exportCurrentProject() {
  const pid = filterProject.value ?? projects.currentId ?? projects.projects[0]?.id
  if (!pid) return
  const p = projects.projects.find(x => x.id === pid)
  if (!p) return
  try {
    await projectsApi.export(p.id, p.name)
  } catch {
    // axios interceptor handles errors
  }
}

async function submitForm() {
  const name = form.value.name.trim()
  if (!name || !form.value.project_id || !form.value.amount || form.value.amount <= 0) return
 if (editingId.value !== null) {
   await costsApi.update(editingId.value, {
   project_id: form.value.project_id,
   name,
   amount: form.value.amount,
   spent_at: form.value.spent_at,
   category: form.value.category,
   task_id: form.value.task_id,
   description: form.value.description || null
   })
  closeForm()
  } else {
  const created = await costsApi.create(form.value.project_id, {
  name,
  amount: form.value.amount,
  spent_at: form.value.spent_at,
  category: form.value.category,
  task_id: form.value.task_id,
  description: form.value.description || null
  })
  for (const f of pendingFiles.value) {
  try {
  await attachmentsApi.upload('cost', created.id, f)
  } catch {
  // axios interceptor alerts; cost itself is already saved
  }
  }
  }
  closeForm()
  await load()
}

async function saveCostName(id: number, name: string) {
 const saved = await costsApi.update(id, { name })
 const index = costs.value.findIndex(cost => cost.id === id)
 if (index !== -1) costs.value[index] = saved
}

async function removeCost(id: number) {
 if (!window.confirm('删除这笔支出?')) return
 await costsApi.remove(id)
 await load()
}

onMounted(async () => {
 if (projects.projects.length === 0) await projects.fetchAll()
 if (categories.list.length === 0) await categories.fetchAll()
 await load()
})
</script>

<style scoped>
.scrollbar-thin::-webkit-scrollbar {
  height: 6px;
}
.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 3px;
}
.scrollbar-thin::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.3);
}
</style>
