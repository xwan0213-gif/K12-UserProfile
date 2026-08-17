<script setup lang="ts">
defineProps<{
  text: string
  priority?: string
}>()
const emit = defineEmits<{
  dismiss: []
  open: []
}>()

function priorityLabel(p?: string) {
  if (p === 'high') return '高优'
  if (p === 'low') return '低优'
  if (p === 'medium') return '中优'
  return p || ''
}
</script>

<template>
  <div
    class="mb-3 flex flex-wrap items-center gap-2 rounded-panel border border-orange-300 bg-orange-50 px-3 py-2 text-[13px]"
    role="status"
  >
    <span class="rounded-control bg-orange-600 px-2 py-0.5 text-xs text-white">弱提醒</span>
    <button
      type="button"
      class="flex min-w-[140px] flex-1 cursor-pointer flex-wrap items-center gap-2 border-none bg-transparent p-0 text-left"
      title="查看日程"
      @click="emit('open')"
    >
      <span class="text-orange-900">{{ text }}</span>
      <span class="whitespace-nowrap text-xs text-fjord">查看日程 →</span>
    </button>
    <span v-if="priority" class="text-xs text-orange-700">{{ priorityLabel(priority) }}</span>
    <button
      type="button"
      class="cursor-pointer rounded-control border border-orange-300 bg-white px-2 py-0.5"
      @click="emit('dismiss')"
    >
      关闭
    </button>
  </div>
</template>
