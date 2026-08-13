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
/** 每行一个时段，如 22:00-08:00 */
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
  <div v-if="open" class="pref">
    <p class="muted">弱提示走侧栏 SSE；强提醒走企微应用消息，无权限时会降级并仅记日志。</p>
    <label>
      <input v-model="weakTip" type="checkbox" />
      侧边栏弱提示
    </label>
    <label>
      <input v-model="strongNotify" type="checkbox" />
      高优强提醒（企微，可降级）
    </label>
    <label class="quiet">
      免打扰时段（每行一个，如 22:00-08:00）
      <textarea v-model="quietText" rows="2" placeholder="22:00-08:00" />
    </label>
    <p v-if="quietPreview.length" class="muted chips">
      将保存：{{ quietPreview.join('、') }}
    </p>
    <div class="actions">
      <button type="button" class="primary" @click="onSave">保存偏好</button>
      <button type="button" @click="emit('update:open', false)">关闭</button>
    </div>
  </div>
</template>

<style scoped>
.pref {
  margin: 8px 0 12px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #f8fafc;
}
.pref label {
  display: flex;
  gap: 6px;
  align-items: center;
  margin: 6px 0;
  font-size: 13px;
}
.quiet {
  flex-direction: column;
  align-items: stretch !important;
}
.quiet textarea {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 8px;
  font: inherit;
  resize: vertical;
}
.muted { color: var(--muted); font-size: 12px; margin: 0 0 6px; }
.chips { margin-top: 4px; }
.actions { display: flex; gap: 8px; margin-top: 8px; }
</style>
