<template>
  <RouterView v-if="bare" />
  <div v-else class="max-w-[1500px] mx-auto p-3 md:p-5 grid grid-cols-1 md:grid-cols-[72px_1fr] gap-3 md:gap-4 min-h-screen">
    <SideRail />
    <div class="flex flex-col gap-4 min-w-0">
      <TopBar />
      <div v-if="auth.user?.must_rotate_password"
        class="rounded-2xl border border-amber-300/70 bg-amber-50/80 px-4 py-3 text-sm text-amber-900">
        这是初始密码。请先到
        <RouterLink to="/settings" class="font-semibold underline">设置</RouterLink>
        修改，然后删除服务器上的初始密码文件。
      </div>
      <RouterView />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import SideRail from '@/components/SideRail.vue'
import TopBar from '@/components/TopBar.vue'
import { useProjectsStore } from '@/stores/projects'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const projects = useProjectsStore()
const auth = useAuthStore()
const bare = computed(() => route.meta.bare === true)

watch(() => auth.user?.workspace_id, (id) => {
  if (id) projects.fetchAll()
}, { immediate: true })
</script>
