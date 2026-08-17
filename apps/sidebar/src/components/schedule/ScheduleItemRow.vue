<script setup lang="ts">
import { ref, shallowRef, watch } from 'vue'
import type { Priority, ScheduleItem } from './types'
import {
  formatWhen,
  fromDatetimeLocal,
  priorityLabel,
  syncLabel,
  toDatetimeLocal,
} from './types'

const props = defineProps<{
  item: ScheduleItem
  busy?: boolean
}>()

const emit = defineEmits<{
  patch: [id: number, body: Record<string, unknown>]
  remind: [id: number, mode: 'weak' | 'strong']
}>()

const editing = shallowRef(false)
const title = ref('')
const startLocal = ref('')
const priority = ref<Priority>('medium')

watch(
  () => props.item,
  (it) => {
    title.value = it.title
    startLocal.value = toDatetimeLocal(it.start_at)
    priority.value = (it.priority as Priority) || 'medium'
    editing.value = false
  },
  { immediate: true },
)

function save() {
  const t = title.value.trim()
  if (!t) return
  emit('patch', props.item.id, {
    title: t,
    start_at: fromDatetimeLocal(startLocal.value),
    priority: priority.value,
  })
  editing.value = false
}

function setStatus(status: 'done' | 'cancelled') {
  const label = status === 'done' ? '完成' : '取消'
  if (!window.confirm(`将待办标记为「${label}」？列表将不再显示已确认中的该项。`)) return
  emit('patch', props.item.id, { status })
}
</script>

<template>
  <li class="flex flex-wrap items-start justify-between gap-2 border-b border-line/60 py-2">
    <div v-if="!editing" class="min-w-0 flex-1">
      <strong class="text-sm text-ink">{{ item.title }}</strong>
      <p class="my-1 text-[13px] text-muted">
        {{ formatWhen(item.start_at) }}
        · {{ priorityLabel(item.priority) }}
        · {{ syncLabel(item.sync_state) }}
        <span v-if="item.source === 'manual'"> · 手工</span>
        <span v-else-if="item.source === 'ai'"> · AI</span>
      </p>
      <p v-if="item.remark" class="my-1 text-xs text-muted">{{ item.remark }}</p>
    </div>
    <div v-else class="grid min-w-[180px] flex-1 gap-1.5">
      <input v-model="title" maxlength="200" class="rounded-control border border-line px-2 py-1.5" />
      <input v-model="startLocal" type="datetime-local" class="rounded-control border border-line px-2 py-1.5" />
      <select v-model="priority" class="rounded-control border border-line px-2 py-1.5">
        <option value="high">高</option>
        <option value="medium">中</option>
        <option value="low">低</option>
      </select>
    </div>
    <div class="flex flex-wrap items-start gap-1.5">
      <template v-if="!editing">
        <button type="button" class="rounded-control border border-line bg-white px-2 py-1 text-xs disabled:opacity-50" :disabled="busy" @click="editing = true">改</button>
        <button type="button" class="rounded-control border border-line bg-white px-2 py-1 text-xs disabled:opacity-50" :disabled="busy" @click="setStatus('done')">完成</button>
        <button type="button" class="rounded-control border border-line bg-white px-2 py-1 text-xs disabled:opacity-50" :disabled="busy" @click="setStatus('cancelled')">取消</button>
        <button type="button" class="rounded-control border border-line bg-white px-2 py-1 text-xs disabled:opacity-50" :disabled="busy" title="侧栏弱提示（SSE）" @click="emit('remind', item.id, 'weak')">弱</button>
        <button type="button" class="rounded-control border border-line bg-white px-2 py-1 text-xs disabled:opacity-50" :disabled="busy" title="企微强提醒（可能降级）" @click="emit('remind', item.id, 'strong')">强</button>
      </template>
      <template v-else>
        <button type="button" class="rounded-control bg-fjord px-2 py-1 text-xs font-semibold text-white disabled:opacity-50" :disabled="busy || !title.trim()" @click="save">保存</button>
        <button type="button" class="rounded-control border border-line bg-white px-2 py-1 text-xs disabled:opacity-50" :disabled="busy" @click="editing = false">取消编辑</button>
      </template>
    </div>
  </li>
</template>
