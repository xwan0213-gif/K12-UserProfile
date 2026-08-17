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
  <div class="my-2.5 rounded-panel border border-line bg-stone-50 p-2.5">
    <p class="m-0 mb-1.5 text-sm">「{{ draft.source_quote || draft.title }}」→ 建议待办</p>
    <p v-if="draft.time_text" class="my-1 text-[13px] text-muted">原文时间：{{ draft.time_text }}</p>
    <div class="my-2 grid gap-2">
      <label class="flex flex-col gap-1 text-xs text-muted">
        标题
        <input v-model="title" maxlength="200" class="rounded-control border border-line px-2 py-1.5 text-ink" />
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
        <input v-model="remark" maxlength="200" class="rounded-control border border-line px-2 py-1.5 text-ink" />
      </label>
    </div>
    <p class="my-1 text-xs text-muted">确认前可改标题/时间；点确认才会写入站内待办。</p>
    <div class="mt-2 flex flex-wrap gap-2">
      <button
        type="button"
        class="rounded-control bg-fjord px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
        :disabled="busy"
        @click="onConfirm(false)"
      >
        确认
      </button>
      <button
        type="button"
        class="rounded-control border border-line bg-white px-3 py-1.5 text-sm disabled:opacity-50"
        :disabled="busy"
        @click="onConfirm(true)"
      >
        确认并同步日历
      </button>
      <button
        type="button"
        class="rounded-control border border-line bg-white px-3 py-1.5 text-sm text-danger disabled:opacity-50"
        :disabled="busy"
        @click="onDismiss"
      >
        忽略
      </button>
    </div>
  </div>
</template>
