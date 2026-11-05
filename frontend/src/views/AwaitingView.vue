<template>
  <GlassCard class="p-6">
    <h2 class="text-xl font-bold">等待分配工作区</h2>
    <p class="mt-2 text-sm text-gray-500">
      账号 {{ auth.user?.email }} 还没有工作区。请联系管理员把你加入一个工作区后再使用项目、任务和费用。
    </p>
  </GlassCard>
</template>

<script setup lang="ts">
import GlassCard from '@/components/GlassCard.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>
