<script setup lang="ts">
import { shallowRef, ref, watch } from 'vue'
import type { Priority } from './types'
import { fromDatetimeLocal } from './types'

const props = defineProps<{
  disabled?: boolean
  /** 父级创建成功后递增，用于收起并清空表单 */
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
  <div class="create">
    <button type="button" :disabled="disabled" @click="open = !open">
      {{ open ? '收起创建' : '手工新建待办' }}
    </button>
    <form v-if="open" class="form" @submit.prevent="submit">
      <label>
        标题
        <input v-model="title" required maxlength="200" placeholder="例如：试听回访" />
      </label>
      <label>
        时间
        <input v-model="startLocal" type="datetime-local" />
      </label>
      <label>
        优先级
        <select v-model="priority">
          <option value="high">高</option>
          <option value="medium">中</option>
          <option value="low">低</option>
        </select>
      </label>
      <label>
        备注
        <input v-model="remark" maxlength="200" placeholder="可选" />
      </label>
      <label class="check">
        <input v-model="syncCalendar" type="checkbox" />
        同步企微日历（失败则站内保留）
      </label>
      <button type="submit" class="primary" :disabled="disabled || !title.trim()">
        创建待办
      </button>
    </form>
  </div>
</template>

<style scoped>
.create { margin: 8px 0 12px; }
.form {
  display: grid;
  gap: 8px;
  margin-top: 8px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #f8fafc;
}
.form label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--muted);
}
.form input,
.form select {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 8px;
  color: var(--ink);
  font: inherit;
}
.form .check {
  flex-direction: row;
  align-items: center;
  gap: 6px;
}
</style>
