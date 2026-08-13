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
  <div class="weak-tip" role="status">
    <span class="label">弱提醒</span>
    <button type="button" class="text-btn" title="查看日程" @click="emit('open')">
      <span class="text">{{ text }}</span>
      <span class="go">查看日程 →</span>
    </button>
    <span v-if="priority" class="prio">{{ priorityLabel(priority) }}</span>
    <button type="button" class="close" @click="emit('dismiss')">关闭</button>
  </div>
</template>

<style scoped>
.weak-tip {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  background: #fff7ed;
  border: 1px solid #fdba74;
  border-radius: 10px;
  padding: 8px 12px;
  margin-bottom: 12px;
  font-size: 13px;
}
.label {
  background: #ea580c;
  color: #fff;
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 12px;
}
.text-btn {
  flex: 1;
  min-width: 140px;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  border: none;
  background: transparent;
  padding: 0;
  text-align: left;
  cursor: pointer;
  color: inherit;
}
.text { color: #9a3412; }
.go {
  color: var(--accent);
  font-size: 12px;
  white-space: nowrap;
}
.prio {
  color: #c2410c;
  font-size: 12px;
}
.close {
  border: 1px solid #fdba74;
  background: #fff;
  border-radius: 6px;
  padding: 2px 8px;
  cursor: pointer;
}
</style>
