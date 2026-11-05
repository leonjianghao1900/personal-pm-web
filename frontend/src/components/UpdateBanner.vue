<template>
 <Teleport to="body">
 <Transition
 enter-active-class="transition-all duration-300 ease-out"
 leave-active-class="transition-all duration-200 ease-in"
 enter-from-class="opacity-0 translate-y-4"
 leave-to-class="opacity-0 translate-y-4">
 <div v-if="show && info"
 class="fixed bottom-5 right-5 z-40 max-w-sm w-[calc(100vw-2.5rem)] bg-white/95 dark:bg-black/85 backdrop-blur-md border border-black/10 dark:border-white/15 rounded-2xl shadow-2xl p-4">
 <div class="flex items-start gap-3">
 <div class="shrink-0 w-9 h-9 rounded-full bg-apple-blue/15 text-apple-blue flex items-center justify-center text-lg">
 ↑
 </div>
 <div class="flex-1 min-w-0">
 <div class="flex items-baseline gap-2 mb-1">
 <span class="font-bold text-sm">发现新版本</span>
 <span class="text-xs text-gray-500 dark:text-gray-400">v{{ info.latest_version }}</span>
 </div>
 <div class="text-xs text-gray-500 dark:text-gray-400 mb-3">
 当前 v{{ info.current_version }}
 </div>
 <div class="flex gap-2">
 <a :href="info.release_url" target="_blank" rel="noopener"
 class="px-3 py-1.5 rounded-lg bg-apple-blue text-white text-xs font-semibold hover:opacity-90">
 查看更新
 </a>
 <button @click="dismiss"
 class="px-3 py-1.5 rounded-lg bg-black/5 dark:bg-white/10 hover:bg-black/10 dark:hover:bg-white/15 text-xs font-medium">
 下次再说
 </button>
 </div>
 </div>
 <button @click="dismiss" title="关闭"
 class="shrink-0 -mt-1 -mr-1 w-6 h-6 rounded-full text-gray-400 hover:bg-black/5 dark:hover:bg-white/10 flex items-center justify-center text-sm">
 ✕
 </button>
 </div>
 </div>
 </Transition>
 </Teleport>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { updatesApi, type UpdateInfo } from '@/api/client'

const STORAGE_KEY = 'pm.update.dismissed'
const info = ref<UpdateInfo | null>(null)
const show = ref(false)

function isDismissed(version: string): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === version
  } catch {
    return false
  }
}

function dismiss() {
  show.value = false
  if (info.value?.latest_version) {
    try {
      localStorage.setItem(STORAGE_KEY, info.value.latest_version)
    } catch {
      /* localStorage may be unavailable in private mode */
    }
  }
}

onMounted(async () => {
  try {
    const result = await updatesApi.check()
    info.value = result
    if (result.has_update && result.latest_version && !isDismissed(result.latest_version)) {
      show.value = true
    }
  } catch {
    /* silent — offline or API hiccup */
  }
})
</script>
