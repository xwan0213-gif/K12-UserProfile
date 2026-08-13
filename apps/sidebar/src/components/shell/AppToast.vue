<script setup lang="ts">
import { useToast } from '../../composables/useToast'

const { toasts, dismiss } = useToast()
</script>

<template>
  <div class="toast-host" aria-live="polite">
    <TransitionGroup name="toast">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="toast"
        :data-kind="t.kind"
        role="status"
      >
        <span class="msg">{{ t.message }}</span>
        <button type="button" class="x" aria-label="关闭" @click="dismiss(t.id)">×</button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-host {
  position: fixed;
  right: 16px;
  bottom: 16px;
  z-index: 80;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: min(360px, calc(100vw - 24px));
  pointer-events: none;
}
.toast {
  pointer-events: auto;
  display: flex;
  gap: 8px;
  align-items: flex-start;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: var(--surface);
  box-shadow: 0 8px 24px rgba(26, 35, 50, 0.12);
  font-size: 13px;
  line-height: 1.4;
  color: var(--ink);
}
.toast[data-kind='ok'] {
  border-color: #99f6e4;
  background: #f0fdfa;
}
.toast[data-kind='warn'] {
  border-color: #fed7aa;
  background: var(--warn-soft);
}
.toast[data-kind='err'] {
  border-color: #fecaca;
  background: var(--danger-soft);
}
.msg { flex: 1; min-width: 0; word-break: break-word; }
.x {
  border: none;
  background: transparent;
  padding: 0 2px;
  line-height: 1;
  font-size: 16px;
  color: var(--muted);
  cursor: pointer;
}
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
