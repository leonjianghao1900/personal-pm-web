<template>
 <div class="space-y-5">
 <GlassCard class="p-5">
 <div class="flex items-center justify-between mb-4">
 <div>
 <h2 class="text-xl font-bold">📥 临时收件箱</h2>
 <p class="text-sm text-gray-500 dark:text-gray-400">插队任务立刻记下，点子灵感随手收藏</p>
 </div>
 <button @click="openCreate"
 class="px-3 py-1.5 rounded-lg bg-apple-blue text-white text-sm font-semibold">
 + 快速添加
 </button>
 </div>

 <div class="flex gap-2 mb-4">
 <button v-for="t in tabs" :key="t.key" @click="tab = t.key"
 :class="['px-4 py-2 rounded-xl text-sm font-semibold transition-colors',
 tab === t.key ? 'bg-apple-blue text-white' : 'bg-black/5 dark:bg-white/10 text-gray-600 hover:bg-black/10 dark:hover:bg-white/10 dark:bg-white/10']">
 {{ t.label }} ({{ counts[t.key] ?? 0 }})
 </button>
 </div>

 <div v-if="shown.length === 0" class="text-center text-sm text-gray-400 dark:text-gray-500 py-12">
 {{ emptyText }}
 </div>

 <div v-else class="space-y-2">
 <div v-for="item in shown" :key="item.id"
 class="flex items-start gap-3 p-3 rounded-xl bg-black/[0.02] dark:bg-white/[0.03] border border-black/5 dark:border-white/10">
 <button @click="toggleComplete(item)"
 class="mt-0.5 w-5 h-5 shrink-0 rounded-full border-2 flex items-center justify-center text-[10px] font-bold transition"
 :class="item.status === 'completed'
 ? 'bg-apple-green border-apple-green text-white'
 : 'border-gray-300 text-transparent hover:border-apple-blue'">
 ✓
 </button>
 <div class="flex-1 min-w-0">
 <div class="flex items-center gap-2">
 <span class="text-sm font-semibold"
 :class="{ 'line-through text-gray-400 dark:text-gray-500': item.status === 'completed' }">
 {{ item.title }}
 </span>
 <span v-if="item.kind === 'interrupt'"
 class="text-[10px] px-1.5 py-0.5 rounded bg-apple-orange/15 text-apple-orange font-semibold">插队</span>
 <span v-else class="text-[10px] px-1.5 py-0.5 rounded bg-apple-purple/15 text-apple-purple font-semibold">点子</span>
 <span class="text-[10px] px-1.5 py-0.5 rounded font-semibold"
 :style="priorityStyle(item.priority)">
 {{ priorityLabel(item.priority) }}
 </span>
 </div>
 <div v-if="item.notes" class="text-xs text-gray-500 dark:text-gray-400 mt-1">{{ item.notes }}</div>
 <div class="flex flex-wrap items-center gap-3 mt-1 text-xs text-gray-400 dark:text-gray-500">
 <span v-if="item.due_at">⏰ {{ formatDue(item.due_at) }}</span>
 <span v-if="item.project_id">{{ projectName(item.project_id) }}</span>
 <span v-if="item.promoted_task_id" class="text-apple-blue">已转正 → 任务 #{{ item.promoted_task_id }}</span>
 </div>
 </div>
 <div class="flex flex-col gap-1 shrink-0">
 <button v-if="item.kind === 'idea' && item.status === 'active'"
 @click="promote(item)"
 class="text-xs px-2 py-1 rounded-lg bg-apple-blue/10 text-apple-blue font-medium hover:bg-apple-blue/20">
 转正为任务
 </button>
 <button @click="openEdit(item)"
 class="text-xs px-2 py-1 rounded-lg bg-black/5 dark:bg-white/10 text-gray-500 dark:text-gray-400 font-medium hover:bg-black/10 dark:hover:bg-white/10 dark:bg-white/10">
 编辑
 </button>
 <button v-if="item.status === 'active' || item.status === 'completed'"
 @click="archive(item)"
 class="text-xs px-2 py-1 rounded-lg bg-black/5 dark:bg-white/10 text-gray-500 dark:text-gray-400 font-medium hover:bg-black/10 dark:hover:bg-white/10 dark:bg-white/10">
 归档
 </button>
 <button @click="remove(item)"
 class="text-xs px-2 py-1 rounded-lg text-red-500 hover:bg-red-500/10">
 删除
 </button>
 </div>
 </div>
 </div>
 </GlassCard>

 <Teleport to="body">
 <div v-if="showForm"
 class="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50"
 @click.self="showForm = false">
 <GlassCard class="p-6 w-[420px]">
 <h3 class="text-lg font-bold mb-4">{{ editingId ? '编辑条目' : '快速添加' }}</h3>
 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">类型</label>
 <div class="grid grid-cols-2 gap-2 mb-3">
 <button @click="form.kind = 'interrupt'"
 :class="['px-3 py-2 rounded-lg text-sm font-semibold border',
 form.kind === 'interrupt'
 ? 'bg-apple-orange/15 border-apple-orange/40 text-apple-orange'
 : 'bg-white/50 dark:bg-white/10 border-black/10 dark:border-white/15 text-gray-500 dark:text-gray-400']">
 🔥 插队任务
 </button>
 <button @click="form.kind = 'idea'"
 :class="['px-3 py-2 rounded-lg text-sm font-semibold border',
 form.kind === 'idea'
 ? 'bg-apple-purple/15 border-apple-purple/40 text-apple-purple'
 : 'bg-white/50 dark:bg-white/10 border-black/10 dark:border-white/15 text-gray-500 dark:text-gray-400']">
 💡 点子
 </button>
 </div>
 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">标题</label>
 <input v-model="form.title" placeholder="记点什么？" @keyup.enter="submitForm"
 class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 mb-3 bg-white/70 dark:bg-white/15" />
 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">备注</label>
 <textarea v-model="form.notes" rows="2" placeholder="补充说明（可选）"
 class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 mb-3 bg-white/70 dark:bg-white/15"></textarea>
 <div class="grid grid-cols-2 gap-3 mb-4">
 <div>
 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">优先级</label>
 <select v-model="form.priority" class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 bg-white/70 dark:bg-white/15">
 <option value="low">低</option>
 <option value="normal">普通</option>
 <option value="high">高</option>
 <option value="urgent">紧急</option>
 </select>
 </div>
 <div v-if="form.kind === 'interrupt'">
 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">提醒时间</label>
 <input v-model="form.due_at" type="datetime-local"
 class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 bg-white/70 dark:bg-white/15" />
 </div>
 </div>
 <div class="flex gap-2 justify-end">
 <button @click="showForm = false" class="px-3 py-1.5 rounded-lg bg-black/5 dark:bg-white/10">取消</button>
 <button @click="submitForm" class="px-3 py-1.5 rounded-lg bg-apple-blue text-white font-semibold">保存</button>
 </div>
 <div v-if="editingId" class="mt-4 pt-3 border-t border-black/5 dark:border-white/10">
 <AttachmentList entity-type="inbox" :entity-id="editingId" />
 </div>
 <div v-else class="mt-4 pt-3 border-t border-black/5 dark:border-white/10">
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
 可附图片或文件，保存时才上传
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
 </GlassCard>
 </div>
 </Teleport>

 <Teleport to="body">
 <div v-if="showPromoteForm && promoteTarget"
 class="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50"
 @click.self="showPromoteForm = false">
 <GlassCard class="p-6 w-96">
 <h3 class="text-lg font-bold mb-1">转正为任务</h3>
 <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">「{{ promoteTarget.title }}」将作为任务加入所选项目</p>
 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">目标项目</label>
 <select v-model="promoteProjectId"
 class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 mb-4 bg-white/70 dark:bg-white/15">
 <option v-for="p in projects.projects" :key="p.id" :value="p.id">{{ p.name }}</option>
 </select>
 <div class="flex gap-2 justify-end">
 <button @click="showPromoteForm = false" class="px-3 py-1.5 rounded-lg bg-black/5 dark:bg-white/10">取消</button>
 <button @click="confirmPromote"
 :disabled="promoteProjectId === null"
 class="px-3 py-1.5 rounded-lg bg-apple-blue text-white font-semibold disabled:opacity-40">
 确认转正
 </button>
 </div>
 </GlassCard>
 </div>
 </Teleport>
 </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import GlassCard from '@/components/GlassCard.vue'
import AttachmentList from '@/components/AttachmentList.vue'
import { attachmentsApi, formatSize, inboxApi } from '@/api/client'
import { useProjectsStore } from '@/stores/projects'
import type { InboxItem, InboxKind, Priority } from '@/api/types'

const projects = useProjectsStore()

const tab = ref<'active' | 'archived'>('active')
const showPromoteForm = ref(false)
const promoteTarget = ref<InboxItem | null>(null)
const promoteProjectId = ref<number | null>(null)

const tabs = [
 { key: 'active', label: '活跃' },
 { key: 'archived', label: '已归档' }
] as const

const showForm = ref(false)
const editingId = ref<number | null>(null)
const form = ref({
 kind: 'idea' as InboxKind,
 title: '',
 notes: '',
 priority: 'normal' as Priority,
 due_at: ''
})

const allItems = ref<InboxItem[]>([])

const counts = computed(() => {
 const active = allItems.value.filter(i => i.status !== 'archived').length
 const archived = allItems.value.filter(i => i.status === 'archived').length
 return { active, archived }
})

const shown = computed(() =>
 tab.value === 'active'
 ? allItems.value.filter(i => i.status !== 'archived')
 : allItems.value.filter(i => i.status === 'archived')
)

const emptyText = computed(() =>
 tab.value === 'active' ? '空空如也，点右上角"快速添加"记下第一条' : '暂无归档内容'
)

const priorityMeta: Record<Priority, { label: string; color: string }> = {
 low: { label: '低', color: '#8e8e93' },
 normal: { label: '普通', color: '#0071e3' },
 high: { label: '高', color: '#ff9500' },
 urgent: { label: '紧急', color: '#ff3b30' }
}

function priorityLabel(p: Priority) {
 return priorityMeta[p]?.label ?? p
}

function priorityStyle(p: Priority) {
 const color = priorityMeta[p]?.color ?? '#8e8e93'
 return { background: color + '22', color }
}

function formatDue(d: string) {
 return d.replace('T', ' ').slice(0, 16)
}

function projectName(id: number) {
 return projects.projects.find(p => p.id === id)?.name ?? `#${id}`
}

async function load() {
 allItems.value = await inboxApi.list()
}

const pendingFiles = ref<File[]>([])
const INBOX_ATTACHMENT_LIMIT = 5
const MAX_FILE_BYTES = 20 * 1024 * 1024

function onPickFiles(e: Event) {
  const target = e.target as HTMLInputElement
  const files = Array.from(target.files ?? [])
  for (const f of files) {
    if (pendingFiles.value.length >= INBOX_ATTACHMENT_LIMIT) break
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

function openCreate() {
  editingId.value = null
  pendingFiles.value = []
  form.value = {
  kind: 'idea',
  title: '',
  notes: '',
  priority: 'normal',
  due_at: ''
  }
  showForm.value = true
}

function openEdit(item: InboxItem) {
 editingId.value = item.id
 const localDue = item.due_at ? item.due_at.slice(0, 16) : ''
 form.value = {
 kind: item.kind,
 title: item.title,
 notes: item.notes ?? '',
 priority: item.priority,
 due_at: localDue
 }
 showForm.value = true
}

async function submitForm() {
 if (!form.value.title.trim()) return
 const payload = {
 kind: form.value.kind,
 title: form.value.title.trim(),
 notes: form.value.notes || null,
 priority: form.value.priority,
 due_at: form.value.due_at ? new Date(form.value.due_at).toISOString() : null
 }
 if (editingId.value !== null) {
 await inboxApi.update(editingId.value, payload)
 } else {
 const created = await inboxApi.create(payload)
 for (const f of pendingFiles.value) {
 try {
 await attachmentsApi.upload('inbox', created.id, f)
 } catch {
 // axios interceptor alerts; item itself is already saved
 }
 }
 }
 showForm.value = false
 editingId.value = null
 pendingFiles.value = []
 await load()
}

async function toggleComplete(item: InboxItem) {
 await inboxApi.update(item.id, {
 status: item.status === 'completed' ? 'active' : 'completed'
 })
 await load()
}

async function archive(item: InboxItem) {
 await inboxApi.update(item.id, { status: 'archived' })
 await load()
}

async function promote(item: InboxItem) {
 promoteTarget.value = item
 promoteProjectId.value = item.project_id ?? projects.projects[0]?.id ?? null
 showPromoteForm.value = true
}

async function confirmPromote() {
 if (!promoteTarget.value || promoteProjectId.value === null) return
 await inboxApi.promote(promoteTarget.value.id, { project_id: promoteProjectId.value })
 showPromoteForm.value = false
 promoteTarget.value = null
 await load()
}

async function remove(item: InboxItem) {
 if (!window.confirm(`删除"${item.title}"?`)) return
 await inboxApi.remove(item.id)
 await load()
}

onMounted(async () => {
 if (projects.projects.length === 0) await projects.fetchAll()
 await load()
})
</script>