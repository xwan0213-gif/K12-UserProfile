<script setup lang="ts">
defineProps<{
  items: Array<{
    key: string
    label: string
    value: string
    hint?: string
    tone?: 'default' | 'up' | 'down' | 'flat'
  }>
}>()
</script>

<template>
  <div class="insight-grid">
    <article v-for="item in items" :key="item.key" class="insight" :data-tone="item.tone || 'default'">
      <span class="label">{{ item.label }}</span>
      <strong class="value">{{ item.value }}</strong>
      <span v-if="item.hint" class="hint">{{ item.hint }}</span>
    </article>
  </div>
</template>

<style scoped>
.insight-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}
.insight {
  background: #f8fafc;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 12px;
  display: grid;
  gap: 4px;
}
.insight[data-tone='up'] {
  background: var(--accent-soft);
  border-color: #99f6e4;
}
.insight[data-tone='down'] {
  background: var(--warn-soft);
  border-color: #fed7aa;
}
.label {
  font-size: 12px;
  color: var(--muted);
}
.value {
  font-size: 1.35rem;
  font-weight: 650;
  color: var(--ink);
  line-height: 1.2;
}
.hint {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.35;
}
@media (max-width: 800px) {
  .insight-grid {
    grid-template-columns: 1fr;
  }
}
</style>
