<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Priority, ScheduleDraft, ScheduleEdits } from './types'
import { fromDatetimeLocal, toDatetimeLocal } from './types'

const props = defineProps<{
  draft: ScheduleDraft
  busy?: boolean
}>()

const emit = defineEmits<{
  confirm: [suggestionId: number, syncCalendar: boolean, edits: ScheduleEdits]
  dismiss: [suggestionId: number]
}>()

const title = ref('')
const startLocal = ref('')
const priority = ref<Priority>('medium')
const remark = ref('')

watch(
  () => props.draft,
  (d) => {
    title.value = d.title || ''
    startLocal.value = toDatetimeLocal(d.start_at)
    priority.value = (d.priority as Priority) || 'medium'
    remark.value = d.predictive_tip || ''
  },
  { immediate: true },
)

function buildEdits(): ScheduleEdits {
  return {
    title: title.value.trim() || props.draft.title || '跟进待办',
    start_at: fromDatetimeLocal(startLocal.value),
    priority: priority.value,
    remark: remark.value.trim() || null,
  }
}

function onConfirm(sync: boolean) {
  emit('confirm', props.draft.suggestion_id, sync, buildEdits())
}

function onDismiss() {
  if (!window.confirm('忽略该 AI 草稿？不会创建站内待办，可稍后重新识别。')) return
  emit('dismiss', props.draft.suggestion_id)
}
</script>

<template>
  <div class="draft">
    <p class="quote">
      「{{ draft.source_quote || draft.title }}」→ 建议待办
    </p>
    <p v-if="draft.time_text" class="muted">原文时间：{{ draft.time_text }}</p>
    <div class="fields">
      <label>
        标题
        <input v-model="title" maxlength="200" />
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
        <input v-model="remark" maxlength="200" />
      </label>
    </div>
    <p class="muted hint">确认前可改标题/时间；点确认才会写入站内待办。</p>
    <div class="actions">
      <button type="button" class="primary" :disabled="busy" @click="onConfirm(false)">
        确认
      </button>
      <button type="button" :disabled="busy" @click="onConfirm(true)">
        确认并同步日历
      </button>
      <button type="button" class="ghost" :disabled="busy" @click="onDismiss">忽略</button>
    </div>
  </div>
</template>

<style scoped>
.draft {
  background: #f8fafc;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px;
  margin: 10px 0;
}
.quote { margin: 0 0 6px; font-size: 14px; }
.muted { color: var(--muted); margin: 4px 0; font-size: 13px; }
.hint { font-size: 12px; }
.fields {
  display: grid;
  gap: 8px;
  margin: 8px 0;
}
.fields label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--muted);
}
.fields input,
.fields select {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 8px;
  color: var(--ink);
  font: inherit;
}
.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.ghost { color: var(--danger); }
</style>
