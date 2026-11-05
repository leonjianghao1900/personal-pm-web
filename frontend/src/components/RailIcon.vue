<template>
 <RouterLink
 :to="to"
 :title="title"
 class="w-12 h-12 rounded-2xl flex items-center justify-center text-xl cursor-pointer
 transition-all hover:bg-black/5 dark:hover:bg-white/10 dark:bg-white/10 hover:scale-105"
 :class="active ? 'bg-gradient-to-br from-apple-blue to-indigo-500 text-white shadow-lg' : 'text-gray-500 dark:text-gray-400'"
 >
 {{ icon }}
 </RouterLink>
</template>

<script setup lang="ts">
defineProps<{ to: string; icon: string; title: string; active?: boolean }>()
</script>
