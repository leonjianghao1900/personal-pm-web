<template>
 <div>
 <div class="flex items-center justify-between mb-2">
 <span class="text-xs text-gray-500 dark:text-gray-400">
 附件 ({{ attachments.length }} / {{ limit }})
 </span>
 <label
 class="px-2.5 py-1 rounded-lg bg-black/5 dark:bg-white/10 hover:bg-black/10 dark:hover:bg-white/15 text-xs font-medium cursor-pointer transition-colors"
 :class="{ 'pointer-events-none opacity-50': attachments.length >= limit }">
 + 添加附件
 <input
 ref="fileInput"
 type="file"
 class="hidden"
 :disabled="attachments.length >= limit"
 @change="onPick" />
 </label>
 </div>

 <div v-if="attachments.length === 0" class="text-xs text-gray-400 dark:text-gray-500 italic py-2">
 暂无附件
 </div>

 <div v-else class="space-y-1.5">
 <div v-for="a in attachments" :key="a.id"
 class="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-black/[0.03] dark:bg-white/[0.04] text-xs">
 <span class="shrink-0 w-7 h-7 rounded-md bg-apple-blue/10 text-apple-blue flex items-center justify-center font-bold">
 {{ iconOf(a) }}
 </span>
 <a :href="downloadUrl(a.id)" target="_blank" rel="noopener"
 class="flex-1 min-w-0 truncate font-medium hover:underline" :title="a.original_name">
 {{ a.original_name }}
 </a>
 <span class="text-gray-400 dark:text-gray-500 shrink-0">{{ formatSize(a.size) }}</span>
 <button @click="onDelete(a.id)"
 class="text-red-500 hover:underline shrink-0">删除</button>
 </div>
 </div>

 <div v-if="errorMsg" class="mt-2 text-xs text-red-500">{{ errorMsg }}</div>
 </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { attachmentsApi, ATTACHMENT_LIMITS, formatSize, type Attachment, type EntityType } from '@/api/client'

const props = defineProps<{
 entityType: EntityType
 entityId: number | null
}>()

const attachments = ref<Attachment[]>([])
const errorMsg = ref<string>('')
const fileInput = ref<HTMLInputElement | null>(null)
const limit = ATTACHMENT_LIMITS[props.entityType]

function iconOf(a: Attachment): string {
 const m = (a.mime || '').toLowerCase()
 if (m.startsWith('image/')) return '🖼'
 if (m === 'application/pdf') return '📕'
 if (m.includes('zip') || m.includes('compressed') || m.includes('rar') || m.includes('7z')) return '🗜'
 if (m.includes('word') || m.includes('document')) return '📄'
 if (m.includes('sheet') || m.includes('excel') || m.includes('csv')) return '📊'
 if (m.startsWith('text/')) return '📝'
 if (m.startsWith('video/')) return '🎬'
 if (m.startsWith('audio/')) return '🎵'
 return '📎'
}

function downloadUrl(id: number): string {
 return attachmentsApi.downloadUrl(id)
}

async function load() {
 if (props.entityId == null) {
 attachments.value = []
 return
 }
 try {
 attachments.value = await attachmentsApi.list(props.entityType, props.entityId)
 } catch {
 // axios interceptor handles toast
 }
}

async function onPick(e: Event) {
 const target = e.target as HTMLInputElement
 const file = target.files?.[0]
 if (!file || props.entityId == null) return
 if (file.size > 20 * 1024 * 1024) {
 errorMsg.value = '文件超过 20 MB 上限'
 target.value = ''
 return
 }
 errorMsg.value = ''
 try {
 await attachmentsApi.upload(props.entityType, props.entityId, file)
 await load()
 } catch {
 // axios interceptor handles toast
 } finally {
 target.value = ''
 }
}

async function onDelete(id: number) {
 if (!window.confirm('删除这个附件?')) return
 try {
 await attachmentsApi.remove(id)
 await load()
 } catch {
 // axios interceptor handles toast
 }
}

onMounted(load)
watch(() => props.entityId, load)
</script>
