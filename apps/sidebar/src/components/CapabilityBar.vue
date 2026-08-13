<script setup lang="ts">
defineProps<{
  flags: {
    mockWecom?: boolean
    mockLlm?: boolean
    llmProvider?: string
    asr?: string
    calendar?: string
    calendarHint?: string
  }
}>()
</script>

<template>
  <div class="cap">
    <span class="brand">擎天学智</span>
    <span class="pill" :class="flags.mockWecom ? 'on' : 'off'">
      企微 {{ flags.mockWecom ? 'Mock' : '实连' }}
    </span>
    <span class="pill">
      LLM {{ flags.mockLlm ? 'Fake' : (flags.llmProvider || 'cloud') }}
    </span>
    <span class="pill">ASR {{ flags.asr || 'Fake' }}</span>
    <span
      class="pill"
      :class="flags.calendar === '可同步' ? 'on' : 'warn'"
      :title="flags.calendarHint || ''"
    >
      日历 {{ flags.calendar || '降级' }}
    </span>
  </div>
</template>

<style scoped>
.cap {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-bottom: 10px;
}
.brand {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 15px;
  margin-right: 4px;
  color: var(--ink);
}
.pill {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  background: #e8eef4;
  color: var(--muted);
}
.pill.on { background: var(--accent-soft); color: var(--accent); }
.pill.warn { background: var(--warn-soft); color: var(--warn); }
.pill.off { background: #e8eef4; color: var(--muted); }
</style>
