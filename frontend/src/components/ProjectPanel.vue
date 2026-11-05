<template>
 <Teleport to="body">
 <Transition name="slide">
 <div v-if="open"
 class="fixed inset-0 z-50 flex justify-end"
 @click.self="onCancel">
 <div class="absolute inset-0 bg-black/30 backdrop-blur-sm" @click="onCancel"></div>
 <GlassCard class="relative w-[440px] h-full overflow-y-auto p-6 rounded-none border-r-0">
 <div class="flex items-center justify-between mb-5">
 <h3 class="text-xl font-bold">{{ isEditing ? '编辑项目' : '新建项目' }}</h3>
 <button @click="onCancel" class="w-8 h-8 rounded-lg bg-black/5 dark:bg-white/10 hover:bg-black/10 dark:hover:bg-white/10 dark:bg-white/10 flex items-center justify-center">✕</button>
 </div>

 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">项目名</label>
 <input ref="nameInput" v-model="form.name" placeholder="项目名"
 @keyup.enter="onSave"
 class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 mb-4 bg-white/70 dark:bg-white/15" />

 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">颜色</label>
 <div class="flex items-center gap-2 mb-4">
 <button v-for="c in presetColors" :key="c"
 @click="form.color = c"
 class="w-7 h-7 rounded-full border-2"
 :class="form.color === c ? 'border-apple-blue' : 'border-white'"
 :style="{ background: c }"></button>
 </div>

 <div class="grid grid-cols-2 gap-3 mb-4">
 <div>
 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">开始日期</label>
 <input v-model="form.start_date" type="date"
 class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 bg-white/70 dark:bg-white/15 text-sm" />
 </div>
 <div>
 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">截止日期</label>
 <input v-model="form.end_date" type="date"
 class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 bg-white/70 dark:bg-white/15 text-sm" />
 </div>
 </div>

 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">备注</label>
 <textarea v-model="form.description" rows="6" placeholder="项目的目标、范围、关键节点…"
 class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 mb-5 bg-white/70 dark:bg-white/15 resize-none"></textarea>

 <div class="flex gap-2 justify-between pt-4 border-t border-black/5 dark:border-white/10">
 <button v-if="isEditing" @click="onDelete"
 class="px-3 py-1.5 rounded-lg bg-red-500/10 text-red-500 text-sm font-medium hover:bg-red-500/20">
 删除项目
 </button>
 <div class="flex gap-2 ml-auto">
 <button @click="onCancel" class="px-3 py-1.5 rounded-lg bg-black/5 dark:bg-white/10 text-sm font-medium">取消</button>
    <button @click="onSave" :disabled="!form.name.trim() || saving"
    class="px-3 py-1.5 rounded-lg bg-apple-blue text-white text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed">
    {{ saving ? '保存中…' : '保存' }}
    </button>
 </div>
 </div>
 </GlassCard>
 </div>
 </Transition>
 </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import GlassCard from '@/components/GlassCard.vue'
import { useProjectsStore } from '@/stores/projects'
import type { Project } from '@/api/types'

const props = defineProps<{
  open: boolean
  project: Project | null
}>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved', project: Project): void
  (e: 'deleted', id: number): void
}>()

const projects = useProjectsStore()

const presetColors = ['#0071e3', '#34c759', '#ff9500', '#af52de', '#ff3b30', '#8e8e93']

const isEditing = computed(() => !!props.project)
const saving = ref(false)

const form = ref({
 name: '', color: '#0071e3',
 start_date: '', end_date: '', description: ''
})

const nameInput = ref<HTMLInputElement | null>(null)

function loadFromProject() {
 if (props.project) {
 form.value = {
 name: props.project.name,
 color: props.project.color,
 start_date: props.project.start_date ?? '',
 end_date: props.project.end_date ?? '',
 description: props.project.description ?? ''
 }
 } else {
 form.value = { name: '', color: '#0071e3', start_date: '', end_date: '', description: '' }
 }
}

function focusName() {
 nextTick(() => nameInput.value?.focus())
}

function onKey(e: KeyboardEvent) {
 if (e.key === 'Escape' && props.open) onCancel()
}

watch(() => props.open, (v) => {
 if (v) { loadFromProject(); focusName() }
})

watch(() => props.project, () => {
 if (props.open) loadFromProject()
})

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))

async function onSave() {
  if (saving.value) return
  if (!form.value.name.trim()) return
  saving.value = true
  const payload = {
    name: form.value.name.trim(),
    color: form.value.color,
    description: form.value.description.trim() || null,
    start_date: form.value.start_date || null,
    end_date: form.value.end_date || null,
  }
  try {
    const saved: Project = props.project
      ? await projects.update(props.project.id, payload)
      : await projects.create(payload)
    emit('saved', saved)
    emit('close')
  } catch { /* interceptor alerts */ }
  finally { saving.value = false }
}

function onCancel() { emit('close') }

async function onDelete() {
  if (!props.project) return
  if (!window.confirm(`删除项目"${props.project.name}"? 所有任务和费用将一并删除`)) return
  const id = props.project.id
  await projects.remove(id)
  emit('deleted', id)
  emit('close')
}
</script>

<style scoped>
.slide-enter-active, .slide-leave-active {
 transition: transform 0.25s ease;
}
.slide-enter-from, .slide-leave-to {
 transform: translateX(100%);
}
</style>