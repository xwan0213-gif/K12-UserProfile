<script setup lang="ts">
import type { FlashKind } from '../composables/useFlash'

defineProps<{
  message: string
  kind?: FlashKind
}>()
</script>

<template>
  <p
    v-if="message"
    role="status"
    aria-live="polite"
    class="m-0 text-sm"
    :class="{
      'text-fjord': kind === 'ok',
      'text-danger': kind === 'err',
      'text-muted': !kind || kind === 'info',
    }"
  >
    {{ message }}
  </p>
</template>
