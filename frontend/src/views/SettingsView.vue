<template>
 <div class="space-y-5">
 <GlassCard class="p-5">
 <h2 class="text-xl font-bold">⚙️ 系统管理</h2>
 <p class="text-sm text-gray-500 dark:text-gray-400">管理应用配置</p>
 </GlassCard>

 <GlassCard class="p-5">
 <h2 class="text-lg font-bold">修改密码</h2>
 <p class="text-sm text-gray-500 dark:text-gray-400 mb-3">首次登录后请立刻更换初始密码，并删除本机的初始密码文件。</p>
 <form class="grid gap-2 md:grid-cols-[1fr_1fr_auto]" @submit.prevent="onChangePassword">
 <input v-model="currentPassword" type="password" required placeholder="当前密码" autocomplete="current-password"
 class="rounded-xl border border-black/10 bg-white/80 px-3 py-2 text-sm" />
 <input v-model="newPassword" type="password" required minlength="10" placeholder="新密码，至少 10 位" autocomplete="new-password"
 class="rounded-xl border border-black/10 bg-white/80 px-3 py-2 text-sm" />
 <button class="rounded-xl bg-apple-blue px-4 py-2 text-sm font-semibold text-white">更新密码</button>
 </form>
 <p v-if="passwordMsg" class="mt-2 text-sm text-gray-600">{{ passwordMsg }}</p>
 </GlassCard>

 <GlassCard v-if="auth.user?.workspace_id" class="p-5">
 <div class="flex items-center justify-between mb-4">
 <div>
 <h2 class="text-lg font-bold">💾 数据管理</h2>
 <p class="text-sm text-gray-500 dark:text-gray-400">下载或恢复只影响当前工作区，不会碰到其他工作区。完整 ZIP 包含 R2 里的附件。</p>
 </div>
 </div>
 <div class="flex flex-wrap items-center gap-2">
 <button @click="onDownload"
 class="px-3 py-1.5 rounded-lg bg-apple-blue text-white text-sm font-semibold">
 下载备份 (JSON)
 </button>
 <button @click="onDownloadFull"
 class="px-3 py-1.5 rounded-lg bg-apple-blue/15 text-apple-blue text-sm font-semibold hover:bg-apple-blue/20">
 下载完整备份 (含附件)
 </button>
 <label class="px-3 py-1.5 rounded-lg bg-black/5 dark:bg-white/10 text-sm font-medium cursor-pointer hover:bg-black/10 dark:hover:bg-white/10 dark:bg-white/10">
 选择备份文件…
 <input type="file" accept=".json,.zip,application/json,application/zip" class="hidden" @change="onFile" />
 </label>
 <span v-if="pendingFile" class="text-xs text-gray-500 dark:text-gray-400">{{ pendingFile.name }}</span>
 <button v-if="pendingFile" @click="onRestore"
 class="px-3 py-1.5 rounded-lg bg-red-500/10 text-red-500 text-sm font-medium hover:bg-red-500/20">
 确认恢复（覆盖现有数据）
 </button>
 </div>
 <p v-if="restoreMsg" class="mt-3 text-sm text-gray-600">{{ restoreMsg }}</p>
 </GlassCard>

 <CostCategoriesView v-if="auth.user?.workspace_id" />

 <div class="text-center text-xs text-gray-400 dark:text-gray-500 pt-2">
 个人 PM {{ APP_VERSION }}
 </div>
 </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import GlassCard from '@/components/GlassCard.vue'
import CostCategoriesView from '@/views/CostCategoriesView.vue'
import { adminApi, authApi } from '@/api/client'
import { APP_VERSION } from '@/version'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const pendingFile = ref<File | null>(null)
const restoreMsg = ref('')
const currentPassword = ref('')
const newPassword = ref('')
const passwordMsg = ref('')

async function onChangePassword() {
  passwordMsg.value = ''
  const updated = await authApi.changePassword(currentPassword.value, newPassword.value)
  auth.setUser(updated)
  currentPassword.value = ''
  newPassword.value = ''
  passwordMsg.value = '密码已更新。请删除初始密码文件，避免明文残留。'
}

function onFile(e: Event) {
 const input = e.target as HTMLInputElement
 pendingFile.value = input.files?.[0] ?? null
 restoreMsg.value = ''
}

async function onDownload() {
 try {
 const blob = await adminApi.backup()
 const url = URL.createObjectURL(blob)
 const a = document.createElement('a')
 a.href = url
 a.download = `pm-backup-${new Date().toISOString().slice(0, 10)}.json`
 document.body.appendChild(a)
 a.click()
 a.remove()
 window.setTimeout(() => URL.revokeObjectURL(url), 1000)
 } catch {
 // Axios 拦截器已提示错误
 }
}

async function onDownloadFull() {
 try {
 const blob = await adminApi.backupFull()
 const url = URL.createObjectURL(blob)
 const a = document.createElement('a')
 a.href = url
 a.download = `pm-backup-full-${new Date().toISOString().slice(0, 10)}.zip`
 document.body.appendChild(a)
 a.click()
 a.remove()
 window.setTimeout(() => URL.revokeObjectURL(url), 1000)
 } catch {
 // Axios 拦截器已提示错误
 }
}

async function onRestore() {
 if (!pendingFile.value) return
 if (!window.confirm('恢复将覆盖现有数据，确定继续？')) return
 try {
 const isZip = pendingFile.value.name.toLowerCase().endsWith('.zip')
 const res = isZip
 ? await adminApi.restoreFull(pendingFile.value)
 : await adminApi.restore(pendingFile.value)
 const total = Object.values(res.counts).reduce((a, b) => a + b, 0)
 restoreMsg.value = `✓ 恢复成功：${total} 条记录已写入，正在刷新…`
 pendingFile.value = null
 window.setTimeout(() => window.location.reload(), 700)
 } catch {
 // Axios 拦截器已提示错误
 }
}
</script>
