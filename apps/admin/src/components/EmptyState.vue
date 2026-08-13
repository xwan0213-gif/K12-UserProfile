<script setup lang="ts">
defineProps<{
  title: string
  hint?: string
}>()
</script>

<template>
  <div class="empty">
    <p class="title">{{ title }}</p>
    <p v-if="hint" class="hint">{{ hint }}</p>
    <slot />
  </div>
</template>

<style scoped>
.empty {
  padding: 20px 16px;
  border: 1px dashed var(--line);
  border-radius: var(--radius);
  background: #fafbfc;
}
.title {
  margin: 0;
  font-size: 14px;
  color: var(--muted);
}
.hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.4;
}
</style>
