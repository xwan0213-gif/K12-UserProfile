<script setup lang="ts">
defineProps<{
  title: string
  hint?: string
}>()
</script>

<template>
  <div class="rounded-panel border border-dashed border-line bg-stone-50 p-4">
    <p class="m-0 text-[13px] leading-snug text-muted">{{ title }}</p>
    <p v-if="hint" class="mt-1.5 text-xs leading-snug text-muted opacity-90">{{ hint }}</p>
    <slot />
  </div>
</template>
