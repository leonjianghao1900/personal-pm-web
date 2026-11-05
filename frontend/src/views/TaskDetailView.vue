<template>
 <div>
 <button @click="$router.back()" class="text-sm text-apple-blue hover:underline mb-3">← 返回</button>

 <GlassCard v-if="task" class="p-6">
 <div class="flex items-center gap-2 mb-4">
 <select v-model="task.status" @change="updateField({ status: task.status })"
 class="px-2 py-1 rounded-lg bg-white/70 dark:bg-white/15 border border-black/10 dark:border-white/15 text-sm font-semibold">
 <option v-for="s in statuses" :key="s.value" :value="s.value">{{ s.label }}</option>
 </select>
 <span class="text-xs px-2 py-0.5 rounded-md bg-apple-orange/20 text-apple-orange font-semibold">
 {{ priorityLabel(task.priority) }}
 </span>
 <button v-if="task.status !== 'done'"
 @click="markDone"
 class="ml-auto px-3 py-1.5 rounded-lg bg-gradient-to-br from-apple-blue to-indigo-500 text-white text-sm font-semibold">
 ✓ 标记完成
 </button>
 </div>

 <EditableName
 :model-value="task.name"
 text-class="text-3xl font-bold tracking-tight w-full max-w-full min-w-0"
 input-class="text-3xl font-bold tracking-tight w-full max-w-full min-w-0"
 :save="saveTaskName"
 class="mb-1"
 />
 <p class="text-sm text-gray-500 dark:text-gray-400 mb-5">项目 #{{ task.project_id }} · 任务 #{{ task.id }}</p>

 <div class="mb-5">
 <div class="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
 <span>进度</span>
 <span class="text-apple-blue font-bold">{{ task.progress }}%</span>
 </div>
 <input type="range" min="0" max="100" step="5" v-model.number="progressVal"
 @change="updateField({ progress: progressVal })"
 class="w-full accent-apple-blue" />
 </div>

 <div class="grid grid-cols-2 md:grid-cols-4 gap-3 p-4 bg-black/[0.02] dark:bg-white/[0.03] rounded-xl mb-5">
 <div>
 <div class="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">开始日期</div>
 <input v-model="dateInputs.start" type="date" @change="saveDates"
 class="w-full px-2 py-1.5 rounded-lg border border-black/10 dark:border-white/15 bg-white/70 dark:bg-white/15 text-sm" />
 </div>
 <div>
 <div class="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">截止日期</div>
 <input v-model="dateInputs.end" type="date" @change="saveDates"
 class="w-full px-2 py-1.5 rounded-lg border border-black/10 dark:border-white/15 bg-white/70 dark:bg-white/15 text-sm" />
 </div>
 <div>
 <div class="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">优先级</div>
 <select v-model="task.priority" @change="updateField({ priority: task.priority })"
 class="w-full px-2 py-1.5 rounded-lg bg-white/70 dark:bg-white/15 border border-black/10 dark:border-white/15 text-sm">
 <option v-for="p in priorityOptions" :key="p.value" :value="p.value">{{ p.label }}</option>
 </select>
 </div>
 <div>
 <div class="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">里程碑</div>
 <label class="inline-flex items-center gap-2 text-sm mt-1 cursor-pointer">
 <input type="checkbox" :checked="task.is_milestone"
 @change="onMilestoneChange($event)" class="accent-apple-blue" />
 {{ task.is_milestone ? '是' : '否' }}
 </label>
 </div>
 </div>

 <div class="mb-5">
 <div v-if="!editingDesc" @click="startEditDesc"
 class="cursor-pointer p-3 rounded-lg hover:bg-black/[0.03] dark:bg-white/[0.04] border border-transparent hover:border-black/5 dark:border-white/10 transition"
 :class="!task.description && 'text-gray-400 dark:text-gray-500 italic'">
 <div v-if="task.description" class="text-sm leading-relaxed whitespace-pre-wrap">
 {{ task.description }}
 </div>
 <div v-else class="text-sm">点击添加描述…</div>
 </div>
 <div v-else>
 <textarea ref="descInput" v-model="descDraft" rows="6"
 class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 bg-white/70 dark:bg-white/15 text-sm resize-none"
 placeholder="任务的背景、目标、注意事项…"></textarea>
 <div class="flex gap-2 justify-end mt-2">
 <button @click="cancelEditDesc" class="px-3 py-1 rounded-lg bg-black/5 dark:bg-white/10 text-xs">取消</button>
 <button @click="saveEditDesc" class="px-3 py-1 rounded-lg bg-apple-blue text-white text-xs font-semibold">保存</button>
 </div>
 </div>
 </div>

 <div class="flex flex-wrap gap-2 pt-4 border-t border-black/5 dark:border-white/10">
 <button @click="resetProgress"
 class="px-3 py-1.5 rounded-lg bg-black/5 dark:bg-white/10 text-sm font-medium hover:bg-black/10 dark:hover:bg-white/10 dark:bg-white/10">
 重置进度
 </button>
 <button @click="remove"
 class="px-3 py-1.5 rounded-lg bg-red-500/10 text-red-500 text-sm font-medium hover:bg-red-500/20">
 删除任务
 </button>
 <button @click="$router.push('/gantt')"
 class="ml-auto px-3 py-1.5 rounded-lg bg-apple-blue/10 text-apple-blue text-sm font-medium hover:bg-apple-blue/15">
 返回甘特图
 </button>
 </div>

 <div v-if="task" class="mt-5 pt-5 border-t border-black/5 dark:border-white/10">
 <AttachmentList entity-type="task" :entity-id="task.id" />
 </div>
 </GlassCard>

 <GlassCard v-else-if="loaded" class="p-8 text-center text-gray-500 dark:text-gray-400">
 任务不存在或已删除
 </GlassCard>

 <GlassCard v-else class="p-8 text-center text-gray-400 dark:text-gray-500">
 加载中...
 </GlassCard>
 </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import GlassCard from '@/components/GlassCard.vue'
import EditableName from '@/components/EditableName.vue'
import AttachmentList from '@/components/AttachmentList.vue'
import { tasksApi } from '@/api/client'
import { useTasksStore } from '@/stores/tasks'
import type { Task, TaskStatus, Priority } from '@/api/types'

const route = useRoute()
const router = useRouter()
const tasksStore = useTasksStore()

const task = ref<Task | null>(null)
const loaded = ref(false)
const progressVal = ref(0)
const dateInputs = ref({ start: '', end: '' })
const editingDesc = ref(false)
const descDraft = ref('')
const descInput = ref<HTMLTextAreaElement | null>(null)

const statuses: { value: TaskStatus; label: string }[] = [
 { value: 'todo', label: '未开始' },
 { value: 'progress', label: '进行中' },
 { value: 'delayed', label: '已延期' },
 { value: 'done', label: '已完成' },
 { value: 'cancelled', label: '已取消' }
]
const priorityOptions: { value: Priority; label: string }[] = [
 { value: 'low', label: '低' },
 { value: 'normal', label: '普通' },
 { value: 'high', label: '高' },
 { value: 'urgent', label: '紧急' }
]
const priorityLabels: Record<Priority, string> = {
 low: '低', normal: '普通', high: '高', urgent: '紧急'
}

function priorityLabel(p: Priority) {
 return priorityLabels[p] ?? p
}

async function load() {
 const tid = Number(route.params.taskId)
 loaded.value = false
 task.value = null
 try {
 task.value = await tasksApi.get(tid)
 progressVal.value = task.value.progress
 dateInputs.value = {
 start: task.value.start_date ?? '',
 end: task.value.end_date ?? ''
 }
 } catch {
 task.value = null
 } finally {
 loaded.value = true
 }
}

async function updateField(payload: Partial<Task>) {
 if (!task.value) return
 task.value = await tasksStore.update(task.value.id, payload)
 if ('progress' in payload) progressVal.value = task.value.progress
}

async function saveTaskName(name: string) {
 if (!task.value) return
 task.value = await tasksStore.update(task.value.id, { name })
}

function onMilestoneChange(e: Event) {
 const checked = (e.target as HTMLInputElement).checked
 updateField({ is_milestone: checked })
}

async function saveDates() {
 if (!task.value) return
 task.value = await tasksStore.update(task.value.id, {
 start_date: dateInputs.value.start || null,
 end_date: dateInputs.value.end || null
 })
}

async function markDone() {
 if (!task.value) return
 await tasksStore.update(task.value.id, { status: 'done', progress: 100 })
 router.push('/gantt')
}

async function resetProgress() {
 if (!task.value) return
 task.value = await tasksStore.update(task.value.id, { progress: 0 })
 progressVal.value = 0
}

function startEditDesc() {
 descDraft.value = task.value?.description ?? ''
 editingDesc.value = true
 nextTick(() => descInput.value?.focus())
}
function cancelEditDesc() {
 editingDesc.value = false
}
async function saveEditDesc() {
 if (!task.value) return
 task.value = await tasksStore.update(task.value.id, {
 description: descDraft.value.trim() || null
 })
 editingDesc.value = false
}

async function remove() {
 if (!task.value) return
 if (!window.confirm(`删除任务"${task.value.name}"?`)) return
 const id = task.value.id
 await tasksStore.remove(id)
 router.push('/gantt')
}

watch(() => route.params.taskId, load, { immediate: true })
</script>
