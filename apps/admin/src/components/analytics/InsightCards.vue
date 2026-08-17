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
  <div class="mb-3.5 grid grid-cols-1 gap-2.5 sm:grid-cols-3">
    <article
      v-for="item in items"
      :key="item.key"
      class="grid gap-1 rounded-panel border border-line p-3"
      :class="{
        'bg-white': !item.tone || item.tone === 'default' || item.tone === 'flat',
        'border-fjord/30 bg-fjord-soft': item.tone === 'up',
        'border-signal/30 bg-stone-50': item.tone === 'down',
      }"
    >
      <span class="text-xs text-muted">{{ item.label }}</span>
      <strong class="text-xl font-semibold leading-tight text-ink">{{ item.value }}</strong>
      <span v-if="item.hint" class="text-xs leading-snug text-muted">{{ item.hint }}</span>
    </article>
  </div>
</template>
