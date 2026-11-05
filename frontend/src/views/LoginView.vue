<template>
  <div class="min-h-screen flex items-center justify-center p-4">
    <GlassCard class="w-full max-w-md p-6 md:p-8">
      <div class="text-2xl font-bold bg-gradient-to-r from-apple-blue to-apple-purple bg-clip-text text-transparent">
        个人 PM
      </div>
      <p class="mt-1 text-sm text-gray-500">登录后进入你所在的工作区。多人可以共用同一个工作区。</p>
      <form class="mt-6 space-y-4" @submit.prevent="onSubmit">
        <label class="block text-sm">
          <span class="text-gray-500">邮箱</span>
          <input v-model="email" type="email" autocomplete="username" required
            class="mt-1 w-full rounded-xl border border-black/10 bg-white/80 px-3 py-2 outline-none focus:border-apple-blue" />
        </label>
        <label class="block text-sm">
          <span class="text-gray-500">密码</span>
          <input v-model="password" type="password" autocomplete="current-password" required
            class="mt-1 w-full rounded-xl border border-black/10 bg-white/80 px-3 py-2 outline-none focus:border-apple-blue" />
        </label>
        <p v-if="error" class="text-sm text-red-500">{{ error }}</p>
        <button type="submit" :disabled="pending"
          class="w-full rounded-xl bg-apple-blue px-3 py-2 text-sm font-semibold text-white disabled:opacity-60">
          {{ pending ? '登录中…' : '登录' }}
        </button>
      </form>
    </GlassCard>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import GlassCard from '@/components/GlassCard.vue'
import { useAuthStore } from '@/stores/auth'

const email = ref('')
const password = ref('')
const error = ref('')
const pending = ref(false)
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

function safeNext(value: string) {
  if (!value.startsWith('/') || value.startsWith('//') || value.startsWith('/login')) return ''
  return value
}

async function onSubmit() {
  error.value = ''
  pending.value = true
  try {
    const user = await auth.login(email.value.trim(), password.value)
    const requested = safeNext(typeof route.query.next === 'string' ? route.query.next : '')
    if (requested) {
      await router.push(requested)
      return
    }
    if (user.workspace_id) await router.push('/dashboard')
    else if (user.role === 'admin') await router.push('/admin/workspaces')
    else await router.push('/awaiting')
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '登录失败'
  } finally {
    pending.value = false
  }
}
</script>
