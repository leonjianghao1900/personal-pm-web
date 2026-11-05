<template>
 <GlassCard class="p-5">
 <div class="flex items-center justify-between mb-4">
 <div>
 <h2 class="text-lg font-bold">🏷️ 费用类别</h2>
 <p class="text-sm text-gray-500 dark:text-gray-400">管理费用类别与颜色，删除已被使用的类别会被拒绝</p>
 </div>
 <button @click="openCreate" class="px-3 py-1.5 rounded-lg bg-apple-blue text-white text-sm font-semibold">
 + 添加类别
 </button>
 </div>

 <div class="space-y-2">
 <div v-if="categories.list.length === 0" class="text-sm text-gray-400 dark:text-gray-500 text-center py-6">
 暂无类别
 </div>
 <div v-for="c in categories.list" :key="c.id"
 class="flex items-center gap-3 p-3 rounded-xl bg-black/[0.02] dark:bg-white/[0.03] border border-black/5 dark:border-white/10">
 <span class="w-4 h-4 rounded-full shrink-0" :style="{ background: c.color }"></span>
 <div class="flex-1">
 <div class="flex items-center gap-2">
 <span class="font-semibold">{{ c.name }}</span>
 <span v-if="c.is_builtin" class="text-[10px] px-1.5 py-0.5 rounded bg-black/5 dark:bg-white/10 text-gray-500 dark:text-gray-400">内置</span>
 </div>
 <span class="text-xs text-gray-400 dark:text-gray-500">{{ c.color }}</span>
 </div>
 <div class="flex items-center gap-1">
 <button v-for="color in presetColors" :key="color" @click="changeColor(c, color)"
 class="w-5 h-5 rounded-full border-2"
 :class="c.color === color ? 'border-apple-blue' : 'border-white'"
 :style="{ background: color }"></button>
 </div>
 <button @click="rename(c)"
 class="text-xs px-2 py-1 rounded-lg bg-black/5 dark:bg-white/10 text-gray-600 hover:bg-black/10 dark:hover:bg-white/10 dark:bg-white/10">改名</button>
 <button @click="remove(c)"
 class="text-xs px-2 py-1 rounded-lg text-red-500 hover:bg-red-500/10">删除</button>
 </div>
 </div>

 <Teleport to="body">
 <div v-if="showForm" class="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50"
 role="dialog" aria-modal="true"
 @click.self="showForm = false">
 <GlassCard class="p-6 w-96">
 <h3 class="text-lg font-bold mb-4">{{ editing?.id ? '重命名类别' : '添加类别' }}</h3>
 <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">类别名</label>
 <input ref="nameInput" v-model="formName" placeholder="如：设计费" @keyup.enter="submitForm"
 class="w-full px-3 py-2 rounded-lg border border-black/10 dark:border-white/15 mb-3 bg-white/70 dark:bg-white/15" />
 <div class="flex gap-2 justify-end">
 <button @click="showForm = false" class="px-3 py-1.5 rounded-lg bg-black/5 dark:bg-white/10">取消</button>
 <button @click="submitForm" :disabled="!formName.trim()"
 class="px-3 py-1.5 rounded-lg bg-apple-blue text-white font-semibold disabled:opacity-50 disabled:cursor-not-allowed">保存</button>
 </div>
 </GlassCard>
 </div>
 </Teleport>
 </GlassCard>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import GlassCard from '@/components/GlassCard.vue'
import { useCategoriesStore } from '@/stores/categories'
import type { CostCategory } from '@/api/types'

const categories = useCategoriesStore()
const presetColors = ['#0071e3', '#34c759', '#ff9500', '#af52de', '#ff3b30', '#8e8e93']

const showForm = ref(false)
const editing = ref<CostCategory | null>(null)
const formName = ref('')
const nameInput = ref<HTMLInputElement | null>(null)

function onKey(e: KeyboardEvent) {
 if (e.key === 'Escape' && showForm.value) showForm.value = false
}

function openCreate() {
 editing.value = null
 formName.value = ''
 showForm.value = true
 nextTick(() => nameInput.value?.focus())
}

function rename(c: CostCategory) {
 editing.value = c
 formName.value = c.name
 showForm.value = true
 nextTick(() => nameInput.value?.focus())
}

async function submitForm() {
 if (!formName.value.trim()) return
 try {
 if (editing.value?.id) {
 await categories.update(editing.value.id, { name: formName.value.trim() })
 } else {
 await categories.create({ name: formName.value.trim(), color: presetColors[0] })
 }
 } catch { /* 409 由 axios 拦截器弹窗提示 */ }
 showForm.value = false
}

async function changeColor(c: CostCategory, color: string) {
 await categories.update(c.id, { color })
}

async function remove(c: CostCategory) {
 if (!window.confirm(`删除类别"${c.name}"?`)) return
 try {
 await categories.remove(c.id)
 } catch { /* 409 由拦截器提示 */ }
}

onMounted(() => { if (categories.list.length === 0) categories.fetchAll() })
onMounted(() => { window.addEventListener('keydown', onKey) })
onUnmounted(() => { window.removeEventListener('keydown', onKey) })
</script>
