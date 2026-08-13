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
  <div v-if="total > 0" class="pager">
    <span class="muted">共 {{ total }} 条 · 第 {{ page }} / {{ totalPages(total, pageSize) }} 页</span>
    <div class="btns">
      <button type="button" :disabled="page <= 1" @click="emit('update:page', page - 1)">
        上一页
      </button>
      <button
        type="button"
        :disabled="page >= totalPages(total, pageSize)"
        @click="emit('update:page', page + 1)"
      >
        下一页
      </button>
    </div>
  </div>
</template>

<style scoped>
.pager {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.btns { display: flex; gap: 6px; }
.muted { color: var(--muted); font-size: 13px; }
</style>
