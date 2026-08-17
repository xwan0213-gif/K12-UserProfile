<script setup lang="ts">
import { shallowRef, ref, watch } from 'vue'
import type { Priority } from './types'
import { fromDatetimeLocal } from './types'

const props = defineProps<{
  disabled?: boolean
  savedTick?: number
}>()

const emit = defineEmits<{
  create: [
    payload: {
      title: string
      start_at: string | null
      priority: Priority
      remark: string | null
      sync_calendar: boolean
    },
  ]
}>()

const open = shallowRef(false)
const title = ref('')
const startLocal = ref('')
const priority = ref<Priority>('medium')
const remark = ref('')
const syncCalendar = shallowRef(false)

function reset() {
  title.value = ''
  startLocal.value = ''
  priority.value = 'medium'
  remark.value = ''
  syncCalendar.value = false
}

watch(
  () => props.savedTick,
  (n, prev) => {
    if (n != null && prev != null && n > prev) {
      reset()
      open.value = false
    }
  },
)

function submit() {
  const t = title.value.trim()
  if (!t || props.disabled) return
  emit('create', {
    title: t,
    start_at: fromDatetimeLocal(startLocal.value),
    priority: priority.value,
    remark: remark.value.trim() || null,
    sync_calendar: syncCalendar.value,
  })
}
</script>

<template>
  <div class="my-2 mb-3">
    <button
      type="button"
      class="rounded-control border border-line bg-white px-3 py-1.5 text-sm disabled:opacity-50"
      :disabled="disabled"
      @click="open = !open"
    >
      {{ open ? '收起创建' : '手工新建待办' }}
    </button>
    <form
      v-if="open"
      class="mt-2 grid gap-2 rounded-panel border border-line bg-stone-50 p-2.5"
      @submit.prevent="submit"
    >
      <label class="flex flex-col gap-1 text-xs text-muted">
        标题
        <input v-model="title" required maxlength="200" placeholder="例如：试听回访" class="rounded-control border border-line px-2 py-1.5 text-ink" />
      </label>
      <label class="flex flex-col gap-1 text-xs text-muted">
        时间
        <input v-model="startLocal" type="datetime-local" class="rounded-control border border-line px-2 py-1.5 text-ink" />
      </label>
      <label class="flex flex-col gap-1 text-xs text-muted">
        优先级
        <select v-model="priority" class="rounded-control border border-line px-2 py-1.5 text-ink">
          <option value="high">高</option>
          <option value="medium">中</option>
          <option value="low">低</option>
        </select>
      </label>
      <label class="flex flex-col gap-1 text-xs text-muted">
        备注
        <input v-model="remark" maxlength="200" placeholder="可选" class="rounded-control border border-line px-2 py-1.5 text-ink" />
      </label>
      <label class="flex flex-row items-center gap-1.5 text-xs text-muted">
        <input v-model="syncCalendar" type="checkbox" />
        同步企微日历（失败则站内保留）
      </label>
      <button
        type="submit"
        class="rounded-control bg-fjord px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
        :disabled="disabled || !title.trim()"
      >
        创建待办
      </button>
    </form>
  </div>
</template>
