<script setup lang="ts">
defineProps<{
  context: any
  customerId: number | null
}>()
</script>

<template>
  <section
    v-if="context"
    class="sticky top-[72px] z-[12] mb-2.5 rounded-panel border border-line border-l-[3px] border-l-fjord bg-white p-3.5 shadow-soft max-md:static"
  >
    <div class="flex items-baseline justify-between gap-2">
      <h2 class="m-0 font-display text-[1.05rem] font-bold leading-snug text-ink">
        {{ context.customer.parent_name }}
        <span class="mx-0.5 font-medium text-muted">/</span>
        {{ context.customer.student_name || '—' }}
      </h2>
    </div>
    <p class="mt-1 text-sm text-muted">
      {{ context.customer.grade || '年级未知' }} · {{ context.customer.school || '学校未知' }}
    </p>
    <div class="mt-2 flex flex-wrap gap-1.5">
      <span
        v-for="t in (context.tags || []).slice(0, 5)"
        :key="t.id"
        class="rounded-control border border-line bg-fjord-soft px-2 py-0.5 text-xs text-fjord"
      >
        {{ t.name }}
      </span>
      <span
        v-if="(context.tags || []).length > 5"
        class="rounded-control border border-line bg-stone-50 px-2 py-0.5 text-xs text-muted"
      >
        +{{ context.tags.length - 5 }}
      </span>
      <span v-if="!(context.tags || []).length" class="text-sm text-muted">暂无标签</span>
    </div>
    <details class="mt-1.5">
      <summary class="cursor-pointer text-xs text-muted">更多信息</summary>
      <p class="mt-1 text-sm text-muted">
        顾问 {{ context.customer.owner_name || '—' }} · 客户 #{{ customerId }}
      </p>
    </details>
  </section>
</template>
