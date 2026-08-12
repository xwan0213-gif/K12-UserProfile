<script setup lang="ts">
defineProps<{
  text: string
  priority?: string
}>()
const emit = defineEmits<{ dismiss: [] }>()
</script>

<template>
  <div class="weak-tip" role="status">
    <span class="label">弱提醒</span>
    <span class="text">{{ text }}</span>
    <span v-if="priority" class="prio">{{ priority }}</span>
    <button type="button" @click="emit('dismiss')">关闭</button>
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
.text { flex: 1; min-width: 120px; color: #9a3412; }
.prio {
  color: #c2410c;
  font-size: 12px;
  text-transform: uppercase;
}
button {
  border: 1px solid #fdba74;
  background: #fff;
  border-radius: 6px;
  padding: 2px 8px;
  cursor: pointer;
}
</style>
