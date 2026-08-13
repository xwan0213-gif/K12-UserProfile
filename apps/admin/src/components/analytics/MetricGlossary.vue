<script setup lang="ts">
defineProps<{
  open?: boolean
}>()
</script>

<template>
  <details class="glossary" :open="open">
    <summary>指标怎么理解？</summary>
    <ul>
      <li><strong>曝光</strong>：侧栏生成并展示过的建议次数。</li>
      <li><strong>复制到企微</strong>：顾问点了复制（真正带走文案）。</li>
      <li><strong>标记有用 / 编辑后有用</strong>：顾问认为建议有价值（含改过再确认）。</li>
      <li><strong>不适用</strong>：顾问明确表示这条不合适。</li>
      <li>
        <strong>采纳率</strong>＝（有用 + 编辑后有用）÷（有用 + 编辑后有用 + 不适用）。未反馈不计入分母。
      </li>
      <li><strong>标签确认/拒绝</strong>：对 AI 推荐标签的接受或跳过。</li>
    </ul>
  </details>
</template>

<style scoped>
.glossary {
  margin-top: 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fafbfc;
  padding: 8px 12px;
}
summary {
  cursor: pointer;
  color: var(--muted);
  font-size: 13px;
}
ul {
  margin: 8px 0 4px;
  padding-left: 18px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
}
strong {
  color: var(--ink);
  font-weight: 600;
}
</style>
