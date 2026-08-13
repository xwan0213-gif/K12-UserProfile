<script setup lang="ts">
defineProps<{
  items: Array<{
    user_id: number
    name: string
    customers: number
    week_actions?: number
  }>
}>()
</script>

<template>
  <ol v-if="items.length" class="rank">
    <li v-for="(a, i) in items" :key="a.user_id">
      <span class="idx">{{ i + 1 }}</span>
      <div class="body">
        <strong>{{ a.name }}</strong>
        <span class="meta">
          客户 {{ a.customers }} 人 · 近 7 日 AI 使用 {{ a.week_actions ?? 0 }} 次
        </span>
      </div>
    </li>
  </ol>
  <p v-else class="muted">暂无顾问排行</p>
</template>

<style scoped>
.rank {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}
li {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fafbfc;
}
.idx {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent);
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 650;
  flex-shrink: 0;
}
.body {
  display: grid;
  gap: 2px;
}
.meta {
  font-size: 12px;
  color: var(--muted);
}
.muted {
  color: var(--muted);
  font-size: 13px;
}
</style>
