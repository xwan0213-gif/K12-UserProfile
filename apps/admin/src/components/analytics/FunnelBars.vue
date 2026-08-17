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
  <div class="grid gap-3">
    <div v-for="s in steps" :key="s.key" class="grid gap-1">
      <div class="flex items-baseline justify-between gap-2">
        <span class="text-sm text-ink">{{ s.title }}</span>
        <strong class="text-base font-semibold">{{ s.count }}</strong>
      </div>
      <div
        class="h-2 overflow-hidden rounded-control bg-stone-100"
        :title="s.note || s.title"
      >
        <div
          class="h-full min-w-0 rounded-control bg-fjord transition-[width]"
          :style="{ width: `${s.pct}%` }"
        />
      </div>
      <p v-if="s.note" class="m-0 text-[11px] leading-snug text-muted">{{ s.note }}</p>
    </div>
  </div>
</template>
