<script setup lang="ts">
defineProps<{
  open?: boolean
}>()
</script>

<template>
  <details
    class="mt-3 rounded-panel border border-line bg-stone-50 px-3 py-2"
    :open="open"
  >
    <summary class="cursor-pointer text-sm text-muted">指标怎么理解？</summary>
    <ul class="mb-1 mt-2 list-disc pl-[18px] text-xs leading-relaxed text-muted">
      <li><strong class="font-semibold text-ink">曝光</strong>：侧栏生成并展示过的建议次数。</li>
      <li><strong class="font-semibold text-ink">复制到企微</strong>：顾问点了复制（真正带走文案）。</li>
      <li>
        <strong class="font-semibold text-ink">标记有用 / 编辑后有用</strong>：顾问认为建议有价值（含改过再确认）。
      </li>
      <li><strong class="font-semibold text-ink">不适用</strong>：顾问明确表示这条不合适。</li>
      <li>
        <strong class="font-semibold text-ink">采纳率</strong>＝（有用 + 编辑后有用）÷（有用 + 编辑后有用 +
        不适用）。未反馈不计入分母。
      </li>
      <li><strong class="font-semibold text-ink">标签确认/拒绝</strong>：对 AI 推荐标签的接受或跳过。</li>
    </ul>
  </details>
</template>
