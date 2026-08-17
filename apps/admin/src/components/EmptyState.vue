<script setup lang="ts">
import type { Component } from 'vue'
import UiIcon from './UiIcon.vue'

defineProps<{
  title: string
  hint?: string
  icon?: Component
}>()
</script>

<template>
  <div
    class="rounded-panel border border-dashed border-line bg-stone-50 px-4 py-5 text-center"
  >
    <UiIcon
      v-if="icon"
      :icon="icon"
      :size="24"
      class="mx-auto mb-2 text-muted"
    />
    <p class="m-0 text-sm text-muted">{{ title }}</p>
    <p v-if="hint" class="mt-1.5 mb-0 text-xs leading-snug text-muted">{{ hint }}</p>
    <div v-if="$slots.default" class="mt-3">
      <slot />
    </div>
  </div>
</template>
