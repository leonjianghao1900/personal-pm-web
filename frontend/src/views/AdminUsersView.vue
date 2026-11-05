<template>
  <div class="space-y-4">
    <GlassCard class="p-5">
      <h2 class="text-xl font-bold">用户</h2>
      <p class="text-sm text-gray-500">管理员可以创建用户，并把每名普通用户放进恰好一个工作区。</p>
      <form class="mt-4 grid gap-3 md:grid-cols-2" @submit.prevent="onCreate">
        <input v-model="form.email" type="email" required placeholder="邮箱"
          class="rounded-xl border border-black/10 bg-white/80 px-3 py-2 text-sm" />
        <input v-model="form.display_name" maxlength="100" placeholder="显示名（可空）"
          class="rounded-xl border border-black/10 bg-white/80 px-3 py-2 text-sm" />
        <input v-model="form.password" type="password" required minlength="10" placeholder="初始密码，至少 10 位"
          class="rounded-xl border border-black/10 bg-white/80 px-3 py-2 text-sm" />
        <div class="flex gap-2">
          <select v-model="form.role" class="rounded-xl border border-black/10 bg-white/80 px-3 py-2 text-sm">
            <option value="user">普通用户</option>
            <option value="admin">管理员</option>
          </select>
          <select v-model="form.workspace_id" class="min-w-0 flex-1 rounded-xl border border-black/10 bg-white/80 px-3 py-2 text-sm">
            <option :value="null">不分配工作区</option>
            <option v-for="ws in workspaces" :key="ws.id" :value="ws.id">{{ ws.name }}</option>
          </select>
        </div>
        <button class="md:col-span-2 rounded-xl bg-apple-blue px-4 py-2 text-sm font-semibold text-white">创建用户</button>
      </form>
    </GlassCard>

    <GlassCard class="p-5 overflow-x-auto">
      <p v-if="loading" class="text-sm text-gray-500">加载中…</p>
      <p v-else-if="error" class="text-sm text-red-500">{{ error }}</p>
      <table v-else class="w-full min-w-[760px] text-sm">
        <thead class="text-left text-gray-500">
          <tr>
            <th class="py-2 pr-3 font-medium">用户</th>
            <th class="py-2 pr-3 font-medium">角色</th>
            <th class="py-2 pr-3 font-medium">工作区</th>
            <th class="py-2 font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id" class="border-t border-black/5 align-top">
            <td class="py-3 pr-3">
              <div class="font-medium">{{ user.display_name }}</div>
              <div class="text-xs text-gray-500">{{ user.email }}</div>
              <div v-if="user.must_rotate_password" class="text-xs text-amber-700">待修改初始密码</div>
            </td>
            <td class="py-3 pr-3">
              <select v-model="drafts[user.id].role" class="rounded-lg border border-black/10 bg-white/70 px-2 py-1.5">
                <option value="user">普通用户</option>
                <option value="admin">管理员</option>
              </select>
            </td>
            <td class="py-3 pr-3">
              <select v-model="drafts[user.id].workspace_id" class="w-full rounded-lg border border-black/10 bg-white/70 px-2 py-1.5">
                <option :value="null">无</option>
                <option v-for="ws in workspaces" :key="ws.id" :value="ws.id">{{ ws.name }}</option>
              </select>
            </td>
            <td class="py-3">
              <div class="flex flex-col gap-2">
                <input v-model="drafts[user.id].password" type="password" placeholder="重置密码（可选）"
                  class="rounded-lg border border-black/10 bg-white/70 px-2 py-1.5" />
                <div class="flex gap-2">
                  <button class="rounded-lg bg-black/5 px-2 py-1" @click="onSave(user.id)">保存</button>
                  <button class="rounded-lg bg-red-500/10 px-2 py-1 text-red-500" @click="onDelete(user.id)">删除</button>
                </div>
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
import type { SessionUser, Workspace } from '@/api/types'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const users = ref<SessionUser[]>([])
const workspaces = ref<Workspace[]>([])
const loading = ref(true)
const error = ref('')
const form = reactive({
  email: '',
  display_name: '',
  password: '',
  role: 'user' as 'admin' | 'user',
  workspace_id: null as number | null,
})
const drafts = reactive<Record<number, { role: 'admin' | 'user'; workspace_id: number | null; password: string }>>({})

function remember(user: SessionUser) {
  drafts[user.id] = {
    role: user.role,
    workspace_id: user.workspace_id,
    password: '',
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [userRows, workspaceRows] = await Promise.all([
      directoryApi.users(),
      directoryApi.workspaces(),
    ])
    users.value = userRows
    workspaces.value = workspaceRows
    for (const user of userRows) remember(user)
  } catch {
    error.value = '用户加载失败'
  } finally {
    loading.value = false
  }
}

function asId(value: number | string | null) {
  if (value == null || value === '' || value === 'null') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

async function onCreate() {
  const workspaceId = asId(form.workspace_id)
  if (form.role === 'user' && workspaceId == null) {
    window.alert('普通用户必须选择一个工作区')
    return
  }
  const created = await directoryApi.createUser({
    email: form.email.trim(),
    password: form.password,
    display_name: form.display_name.trim() || undefined,
    role: form.role,
    workspace_id: workspaceId,
  })
  users.value.push(created)
  remember(created)
  form.email = ''
  form.display_name = ''
  form.password = ''
  form.role = 'user'
  form.workspace_id = null
}

async function onSave(id: number) {
  const draft = drafts[id]
  const payload: { role: 'admin' | 'user'; workspace_id: number | null; password?: string } = {
    role: draft.role,
    workspace_id: asId(draft.workspace_id),
  }
  if (draft.password.trim()) payload.password = draft.password.trim()
  const updated = await directoryApi.updateUser(id, payload)
  const index = users.value.findIndex(user => user.id === id)
  if (index >= 0) users.value[index] = updated
  remember(updated)
  if (auth.user?.id === id) auth.setUser(updated)
}

async function onDelete(id: number) {
  if (!window.confirm('删除这个用户？')) return
  await directoryApi.removeUser(id)
  users.value = users.value.filter(user => user.id !== id)
}

onMounted(load)
</script>
