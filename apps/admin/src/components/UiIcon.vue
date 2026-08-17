<script setup lang="ts">
import { computed } from 'vue'
import type { Component } from 'vue'

const props = withDefaults(
  defineProps<{
    icon: Component
    size?: number
    strokeWidth?: number
    class?: string
  }>(),
  {
    size: 20,
    strokeWidth: 1.5,
  },
)

const cls = computed(() => props.class || undefined)
</script>

<template>
  <component
    :is="icon"
    :size="size"
    :stroke-width="strokeWidth"
    :class="cls"
    aria-hidden="true"
  />
</template>
