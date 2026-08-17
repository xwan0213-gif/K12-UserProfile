<script setup lang="ts">
defineProps<{
  page: number
  pageSize: number
  total: number
}>()

const emit = defineEmits<{
  'update:page': [n: number]
}>()

function totalPages(total: number, pageSize: number) {
  return Math.max(1, Math.ceil((total || 0) / (pageSize || 1)))
}
</script>

<template>
  <div
    v-if="total > 0"
    class="mt-3 flex flex-wrap items-center justify-between gap-2"
  >
    <span class="text-sm text-muted">
      共 {{ total }} 条 · 第 {{ page }} / {{ totalPages(total, pageSize) }} 页
    </span>
    <div class="flex gap-1.5">
      <button
        type="button"
        class="rounded-control border border-line bg-white px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-50"
        aria-label="上一页"
        :disabled="page <= 1"
        @click="emit('update:page', page - 1)"
      >
        上一页
      </button>
      <button
        type="button"
        class="rounded-control border border-line bg-white px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-50"
        aria-label="下一页"
        :disabled="page >= totalPages(total, pageSize)"
        @click="emit('update:page', page + 1)"
      >
        下一页
      </button>
    </div>
  </div>
</template>
