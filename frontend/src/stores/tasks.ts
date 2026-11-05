import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { tasksApi, depsApi } from '@/api/client'
import type { TaskInput } from '@/api/client'
import type { Task, TaskDependency } from '@/api/types'

export const useTasksStore = defineStore('tasks', () => {
  const tasks = ref<Task[]>([])
  const dependencies = ref<TaskDependency[]>([])

  const byId = computed(() => {
    const m = new Map<number, Task>()
    tasks.value.forEach(t => m.set(t.id, t))
    return m
  })

  const roots = computed(() => tasks.value.filter(t => t.parent_id === null))

  async function fetchByProject(projectId: number) {
    tasks.value = await tasksApi.listByProject(projectId)
    dependencies.value = await depsApi.listByProject(projectId)
  }

  async function fetchAll() {
    const { projectsApi } = await import('@/api/client')
    const plist = await projectsApi.list()
    const result: Task[] = []
    const deps: TaskDependency[] = []
    for (const p of plist) {
      result.push(...await tasksApi.listByProject(p.id))
      deps.push(...await depsApi.listByProject(p.id))
    }
    tasks.value = result
    dependencies.value = deps
  }

  async function create(projectId: number, data: TaskInput) {
    const t = await tasksApi.create(projectId, data)
    tasks.value.push(t)
    return t
  }

  async function update(id: number, data: TaskInput) {
    const t = await tasksApi.update(id, data)
    const idx = tasks.value.findIndex(x => x.id === id)
    if (idx >= 0) tasks.value[idx] = t
    return t
  }

  async function move(id: number, start: string, end: string) {
    const t = await tasksApi.move(id, start, end)
    const idx = tasks.value.findIndex(x => x.id === id)
    if (idx >= 0) tasks.value[idx] = t
  }

  async function remove(id: number) {
    await tasksApi.remove(id)
    tasks.value = tasks.value.filter(t => t.id !== id)
    dependencies.value = dependencies.value.filter(
      d => d.predecessor_id !== id && d.successor_id !== id
    )
  }

  async function addDependency(taskId: number, predecessorId: number) {
    const d = await depsApi.add(taskId, predecessorId)
    if (!dependencies.value.some(x => x.id === d.id)) {
      dependencies.value.push(d)
    }
    return d
  }

  function predecessorsOf(taskId: number): number[] {
    return dependencies.value
      .filter(d => d.successor_id === taskId)
      .map(d => d.predecessor_id)
  }

  return {
    tasks, dependencies, byId, roots,
    fetchByProject, fetchAll,
    create, update, move, remove,
    addDependency, predecessorsOf
  }
})
