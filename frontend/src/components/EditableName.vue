<template>
 <button
 v-if="!editing"
 v-bind="$attrs"
 type="button"
 :aria-label="label"
 class="rounded bg-transparent text-left transition-colors hover:bg-black/5 dark:hover:bg-white/10 dark:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-apple-blue/30"
 :class="textClass"
 @click="start"
 >
 {{ modelValue }}
 </button>
 <input
 v-else
 v-bind="$attrs"
 ref="input"
 v-model="draft"
 :aria-label="label"
 maxlength="200"
 :disabled="saving"
 class="rounded-lg border border-black/10 dark:border-white/15 bg-white/70 dark:bg-white/15 px-2 py-1 focus:border-apple-blue focus:outline-none focus:ring-2 focus:ring-apple-blue/20 disabled:cursor-wait disabled:opacity-60"
 :class="inputClass"
 @keydown.enter.prevent="commit"
 @keydown.escape.prevent="cancel"
 @blur="commit"
 />
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'

defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
 modelValue: string
 textClass?: string
 inputClass?: string
 save: (name: string) => Promise<void>
}>(), {
 textClass: '',
 inputClass: ''
})

const editing = ref(false)
const draft = ref('')
const saving = ref(false)
const input = ref<HTMLInputElement | null>(null)
const label = computed(() => `修改名称：${props.modelValue}`)

async function start() {
 draft.value = props.modelValue
 editing.value = true
 await nextTick()
 input.value?.focus()
 input.value?.select()
}

function cancel() {
 draft.value = props.modelValue
 editing.value = false
}

async function commit() {
 if (!editing.value || saving.value) return

 const name = draft.value.trim()
 if (!name) return
 if (name === props.modelValue) {
 editing.value = false
 return
 }

 saving.value = true
 try {
 await props.save(name)
 editing.value = false
 } catch {
 saving.value = false
 await nextTick()
 input.value?.focus()
 } finally {
 saving.value = false
 }
}
</script>
