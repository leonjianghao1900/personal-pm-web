<template>
  <div class="space-y-4">
    <GlassCard class="p-5">
      <h2 class="text-xl font-bold">工作区</h2>
      <p class="text-sm text-gray-500">一个工作区里可以有多名用户。普通用户必须且只能属于一个工作区。</p>
      <form class="mt-4 flex flex-col gap-2 sm:flex-row" @submit.prevent="onCreate">
        <input v-model="name" required maxlength="100" placeholder="例如：家庭装修"
          class="flex-1 rounded-xl border border-black/10 bg-white/80 px-3 py-2 text-sm outline-none focus:border-apple-blue" />
        <button class="rounded-xl bg-apple-blue px-4 py-2 text-sm font-semibold text-white">创建工作区</button>
      </form>
      <p v-if="!auth.user?.workspace_id" class="mt-3 text-sm text-amber-700">
        当前管理员还没有工作区，项目数据不可见。创建后点「设为我的工作区」。
      </p>
    </GlassCard>

    <GlassCard class="p-5 overflow-x-auto">
      <p v-if="loading" class="text-sm text-gray-500">加载中…</p>
      <p v-else-if="error" class="text-sm text-red-500">{{ error }}</p>
      <table v-else class="w-full min-w-[640px] text-sm">
        <thead class="text-left text-gray-500">
          <tr>
            <th class="py-2 pr-3 font-medium">名称</th>
            <th class="py-2 pr-3 font-medium">成员</th>
            <th class="py-2 font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ws in rows" :key="ws.id" class="border-t border-black/5">
            <td class="py-3 pr-3">
              <input v-model="drafts[ws.id]" maxlength="100"
                class="w-full rounded-lg border border-black/10 bg-white/70 px-2 py-1.5" />
            </td>
            <td class="py-3 pr-3">{{ ws.member_count }}</td>
            <td class="py-3">
              <div class="flex flex-wrap gap-2">
                <button class="rounded-lg bg-black/5 px-2 py-1" @click="onRename(ws.id)">保存</button>
                <button class="rounded-lg bg-apple-blue/10 px-2 py-1 text-apple-blue" @click="onUse(ws.id)">
                  {{ auth.user?.workspace_id === ws.id ? '当前工作区' : '设为我的工作区' }}
                </button>
                <button class="rounded-lg bg-red-500/10 px-2 py-1 text-red-500" @click="onDelete(ws)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </GlassCard>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import GlassCard from '@/components/GlassCard.vue'
import { directoryApi } from '@/api/client'
import type { Workspace } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { useProjectsStore } from '@/stores/projects'

const auth = useAuthStore()
const projects = useProjectsStore()
const rows = ref<Workspace[]>([])
const drafts = reactive<Record<number, string>>({})
const name = ref('')
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await directoryApi.workspaces()
    for (const ws of rows.value) drafts[ws.id] = ws.name
  } catch {
    error.value = '工作区加载失败'
  } finally {
    loading.value = false
  }
}

async function onCreate() {
  const created = await directoryApi.createWorkspace(name.value.trim())
  name.value = ''
  rows.value.push(created)
  drafts[created.id] = created.name
}

async function onRename(id: number) {
  const updated = await directoryApi.updateWorkspace(id, drafts[id].trim())
  const index = rows.value.findIndex(row => row.id === id)
  if (index >= 0) rows.value[index] = updated
  if (auth.user?.workspace_id === id) await auth.fetchMe()
}

async function onUse(id: number) {
  if (!auth.user) return
  const updated = await directoryApi.updateUser(auth.user.id, { workspace_id: id })
  auth.setUser(updated)
  await projects.fetchAll()
}

async function onDelete(ws: Workspace) {
  if (!window.confirm(`删除工作区「${ws.name}」？有成员时会拒绝删除。`)) return
  await directoryApi.removeWorkspace(ws.id)
  rows.value = rows.value.filter(row => row.id !== ws.id)
}

onMounted(load)
</script>
