<script setup lang="ts">
import { useToast } from '../../composables/useToast'

const { toasts, dismiss } = useToast()
</script>

<template>
  <div
    class="pointer-events-none fixed bottom-4 right-4 z-[80] flex max-w-[min(360px,calc(100vw-24px))] flex-col gap-2"
    aria-live="polite"
  >
    <TransitionGroup
      enter-active-class="transition duration-[180ms] ease-out"
      leave-active-class="transition duration-[180ms] ease-out"
      enter-from-class="translate-y-2 opacity-0"
      leave-to-class="translate-y-2 opacity-0"
    >
      <div
        v-for="t in toasts"
        :key="t.id"
        class="pointer-events-auto flex items-start gap-2 rounded-panel border border-line bg-white px-3 py-2.5 text-[13px] leading-snug text-ink shadow-[0_8px_24px_rgba(26,35,50,0.12)]"
        :class="{
          'border-teal-200 bg-teal-50': t.kind === 'ok',
          'border-orange-200 bg-orange-50': t.kind === 'warn',
          'border-red-200 bg-red-50': t.kind === 'err',
        }"
        role="status"
      >
        <span class="min-w-0 flex-1 break-words">{{ t.message }}</span>
        <button
          type="button"
          class="cursor-pointer border-none bg-transparent px-0.5 text-base leading-none text-muted"
          aria-label="关闭"
          @click="dismiss(t.id)"
        >
          ×
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>
