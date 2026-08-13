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
  <li class="row">
    <div class="body" v-if="!editing">
      <strong>{{ item.title }}</strong>
      <p class="muted">
        {{ formatWhen(item.start_at) }}
        · {{ priorityLabel(item.priority) }}
        · {{ syncLabel(item.sync_state) }}
        <span v-if="item.source === 'manual'"> · 手工</span>
        <span v-else-if="item.source === 'ai'"> · AI</span>
      </p>
      <p v-if="item.remark" class="muted remark">{{ item.remark }}</p>
    </div>
    <div v-else class="edit">
      <input v-model="title" maxlength="200" />
      <input v-model="startLocal" type="datetime-local" />
      <select v-model="priority">
        <option value="high">高</option>
        <option value="medium">中</option>
        <option value="low">低</option>
      </select>
    </div>
    <div class="actions">
      <template v-if="!editing">
        <button type="button" :disabled="busy" @click="editing = true">改</button>
        <button type="button" :disabled="busy" @click="setStatus('done')">完成</button>
        <button type="button" :disabled="busy" @click="setStatus('cancelled')">取消</button>
        <button type="button" :disabled="busy" title="侧栏弱提示（SSE）" @click="emit('remind', item.id, 'weak')">
          弱
        </button>
        <button type="button" :disabled="busy" title="企微强提醒（可能降级）" @click="emit('remind', item.id, 'strong')">
          强
        </button>
      </template>
      <template v-else>
        <button type="button" class="primary" :disabled="busy || !title.trim()" @click="save">
          保存
        </button>
        <button type="button" :disabled="busy" @click="editing = false">取消编辑</button>
      </template>
    </div>
  </li>
</template>

<style scoped>
.row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #eef2f6;
  flex-wrap: wrap;
}
.body { min-width: 0; flex: 1; }
.muted { color: var(--muted); margin: 4px 0; font-size: 13px; }
.remark { font-size: 12px; }
.actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: flex-start;
}
.actions button { font-size: 12px; padding: 4px 8px; }
.edit {
  display: grid;
  gap: 6px;
  flex: 1;
  min-width: 180px;
}
.edit input,
.edit select {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 8px;
  font: inherit;
}
</style>
