<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { RemindPref } from './types'

const props = defineProps<{
  pref: RemindPref
  open: boolean
}>()

const emit = defineEmits<{
  'update:open': [v: boolean]
  save: [pref: RemindPref]
}>()

const weakTip = ref(true)
const strongNotify = ref(true)
const quietText = ref('')

watch(
  () => props.pref,
  (p) => {
    weakTip.value = p.weak_tip !== false
    strongNotify.value = p.strong_notify !== false
    quietText.value = (p.quiet_hours || []).join('\n')
  },
  { immediate: true, deep: true },
)

const quietPreview = computed(() =>
  quietText.value
    .split(/[\n,，]+/)
    .map((s) => s.trim())
    .filter(Boolean),
)

function onSave() {
  emit('save', {
    weak_tip: weakTip.value,
    strong_notify: strongNotify.value,
    quiet_hours: quietPreview.value,
  })
}
</script>

<template>
  <div v-if="open" class="my-2 mb-3 rounded-panel border border-line bg-stone-50 p-2.5">
    <p class="mb-1.5 text-xs text-muted">弱提示走侧栏 SSE；强提醒走企微应用消息，无权限时会降级并仅记日志。</p>
    <label class="my-1.5 flex items-center gap-1.5 text-[13px]">
      <input v-model="weakTip" type="checkbox" />
      侧边栏弱提示
    </label>
    <label class="my-1.5 flex items-center gap-1.5 text-[13px]">
      <input v-model="strongNotify" type="checkbox" />
      高优强提醒（企微，可降级）
    </label>
    <label class="my-1.5 flex flex-col gap-1 text-[13px] text-muted">
      免打扰时段（每行一个，如 22:00-08:00）
      <textarea
        v-model="quietText"
        rows="2"
        placeholder="22:00-08:00"
        class="resize-y rounded-control border border-line px-2 py-1.5 text-ink"
      />
    </label>
    <p v-if="quietPreview.length" class="mt-1 text-xs text-muted">将保存：{{ quietPreview.join('、') }}</p>
    <div class="mt-2 flex gap-2">
      <button type="button" class="rounded-control bg-fjord px-3 py-1.5 text-sm font-semibold text-white" @click="onSave">
        保存偏好
      </button>
      <button
        type="button"
        class="rounded-control border border-line bg-white px-3 py-1.5 text-sm"
        @click="emit('update:open', false)"
      >
        关闭
      </button>
    </div>
  </div>
</template>
