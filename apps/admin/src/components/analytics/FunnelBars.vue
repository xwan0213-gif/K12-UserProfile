<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  funnel: {
    lead?: number
    intent?: number
    trial?: number
    deal?: number
  }
  labels?: Record<string, string>
}>()

const steps = computed(() => {
  const f = props.funnel || {}
  const lead = f.lead ?? 0
  const max = Math.max(lead, 1)
  const defs = [
    { key: 'lead', title: '线索', count: f.lead ?? 0 },
    { key: 'intent', title: '意向', count: f.intent ?? 0 },
    { key: 'trial', title: '体验', count: f.trial ?? 0 },
    { key: 'deal', title: '成交', count: f.deal ?? 0 },
  ]
  return defs.map((d) => ({
    ...d,
    pct: Math.min(100, Math.round((d.count / max) * 100)),
    note: props.labels?.[d.key],
  }))
})
</script>

<template>
  <div class="funnel">
    <div v-for="s in steps" :key="s.key" class="step">
      <div class="head">
        <span class="title">{{ s.title }}</span>
        <strong>{{ s.count }}</strong>
      </div>
      <div class="track" :title="s.note || s.title">
        <div class="fill" :style="{ width: `${s.pct}%` }" />
      </div>
      <p v-if="s.note" class="note">{{ s.note }}</p>
    </div>
  </div>
</template>

<style scoped>
.funnel {
  display: grid;
  gap: 12px;
}
.step {
  display: grid;
  gap: 4px;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
}
.title {
  font-size: 13px;
  color: var(--ink);
}
.head strong {
  font-size: 1.05rem;
}
.track {
  height: 10px;
  background: #e8eef4;
  border-radius: 999px;
  overflow: hidden;
}
.fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), #14b8a6);
  border-radius: 999px;
  min-width: 0;
}
.note {
  margin: 0;
  font-size: 11px;
  color: var(--muted);
  line-height: 1.35;
}
</style>
