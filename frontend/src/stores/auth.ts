import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/client'
import type { SessionUser } from '@/api/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<SessionUser | null>(null)
  const loaded = ref(false)

  const isAdmin = computed(() => user.value?.role === 'admin')
  const workspaceId = computed(() => user.value?.workspace_id ?? null)

  async function fetchMe() {
    try {
      user.value = await authApi.me()
    } catch {
      user.value = null
    } finally {
      loaded.value = true
    }
  }

  async function login(email: string, password: string) {
    const result = await authApi.login(email, password)
    user.value = result.user
    loaded.value = true
    return result.user
  }

  async function logout() {
    try {
      await authApi.logout()
    } finally {
      user.value = null
    }
  }

  function setUser(next: SessionUser | null) {
    user.value = next
  }

  return { user, loaded, isAdmin, workspaceId, fetchMe, login, logout, setUser }
})
