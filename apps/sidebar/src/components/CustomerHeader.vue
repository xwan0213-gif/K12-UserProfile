<script setup lang="ts">
defineProps<{
  context: any
  customerId: number | null
}>()
</script>

<template>
  <section v-if="context" class="head card">
    <div class="title">
      <strong>
        {{ context.customer.parent_name }}
        <span class="sep">/</span>
        {{ context.customer.student_name || '—' }}
      </strong>
      <span class="meta">
        {{ context.customer.grade || '—' }} · {{ context.customer.school || '—' }}
      </span>
    </div>
    <div class="tags">
      <span v-for="t in (context.tags || []).slice(0, 5)" :key="t.id" class="chip">{{ t.name }}</span>
      <span v-if="(context.tags || []).length > 5" class="chip">+{{ context.tags.length - 5 }}</span>
      <span v-if="!(context.tags || []).length" class="muted">暂无标签</span>
    </div>
    <details class="more">
      <summary>详情</summary>
      <p class="muted">顾问：{{ context.customer.owner_name || '—' }} · customer_id={{ customerId }}</p>
    </details>
  </section>
</template>

<style scoped>
.card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 12px;
  margin-bottom: 10px;
  box-shadow: var(--shadow);
}
.title {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  justify-content: space-between;
}
.sep { color: var(--muted); margin: 0 2px; }
.meta { color: var(--muted); font-size: 13px; }
.tags { margin-top: 8px; }
.more { margin-top: 6px; }
.more summary {
  cursor: pointer;
  color: var(--muted);
  font-size: 12px;
}
</style>
