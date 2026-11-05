import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { categoriesApi } from '@/api/client'
import type { CostCategory } from '@/api/types'

export const useCategoriesStore = defineStore('categories', () => {
  const list = ref<CostCategory[]>([])

  const byName = computed(() => {
    const m = new Map<string, CostCategory>()
    list.value.forEach(c => m.set(c.name, c))
    return m
  })

  function colorOf(name: string): string {
    return byName.value.get(name)?.color ?? '#8e8e93'
  }

  async function fetchAll() {
    list.value = await categoriesApi.list()
  }

  async function create(data: { name: string; color: string }) {
    const c = await categoriesApi.create(data)
    list.value.push(c)
    return c
  }

  async function update(id: number, data: Partial<Pick<CostCategory, 'name' | 'color' | 'sort_order'>>) {
    const c = await categoriesApi.update(id, data)
    const idx = list.value.findIndex(x => x.id === id)
    if (idx >= 0) list.value[idx] = c
    return c
  }

  async function remove(id: number) {
    await categoriesApi.remove(id)
    list.value = list.value.filter(c => c.id !== id)
  }

  return { list, byName, colorOf, fetchAll, create, update, remove }
})