<template>
 <span :class="['inline-block text-xs font-semibold px-2 py-0.5 rounded-md', cls]">
 {{ label }}
 </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TaskStatus } from '@/api/types'

const props = defineProps<{ status: TaskStatus }>()

const map: Record<TaskStatus, { cls: string; label: string }> = {
 todo: { cls: 'bg-gray-100 text-gray-700 dark:text-gray-200', label: '未开始' },
 progress: { cls: 'bg-apple-blue/15 text-apple-blue', label: '进行中' },
 delayed: { cls: 'bg-apple-orange/20 text-apple-orange', label: '延期' },
 done: { cls: 'bg-apple-green/20 text-apple-green', label: '已完成' },
 cancelled: { cls: 'bg-apple-purple/15 text-apple-purple', label: '已取消' }
}
const cls = computed(() => map[props.status]?.cls ?? map.todo.cls)
const label = computed(() => map[props.status]?.label ?? map.todo.label)
</script>
