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
  <ol v-if="items.length" class="m-0 grid list-none gap-2 p-0">
    <li
      v-for="(a, i) in items"
      :key="a.user_id"
      class="flex items-start gap-2.5 rounded-panel border border-line bg-stone-50 p-2.5"
    >
      <span
        class="grid h-6 w-6 shrink-0 place-items-center rounded-control bg-fjord-soft text-xs font-semibold text-fjord"
      >
        {{ i + 1 }}
      </span>
      <div class="grid gap-0.5">
        <strong class="text-sm">{{ a.name }}</strong>
        <span class="text-xs text-muted">
          客户 {{ a.customers }} 人 · 近 7 日 AI 使用 {{ a.week_actions ?? 0 }} 次
        </span>
      </div>
    </li>
  </ol>
  <p v-else class="text-sm text-muted">暂无顾问排行</p>
</template>
