<script setup lang="ts">
import { onMounted, ref } from 'vue'
import EmptyState from '../components/EmptyState.vue'
import { useAuth } from '../composables/useAuth'

const { api } = useAuth()
const data = ref<any>(null)
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  loading.value = true
  error.value = ''
  try {
    data.value = await api('/admin/dashboard/summary')
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="card">
    <h2>看板</h2>
    <p v-if="loading" class="muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" hint="若无权限或会话过期，请重新登录。" />
    <template v-else-if="data">
      <div class="grid">
        <div><span>线索</span><strong>{{ data.funnel?.lead ?? 0 }}</strong></div>
        <div><span>意向</span><strong>{{ data.funnel?.intent ?? 0 }}</strong></div>
        <div><span>试听</span><strong>{{ data.funnel?.trial ?? 0 }}</strong></div>
        <div><span>成交</span><strong>{{ data.funnel?.deal ?? 0 }}</strong></div>
      </div>
      <p class="muted">续费率（MVP 口径）：{{ data.renewal_rate }}</p>
      <h3>顾问人效 Top</h3>
      <ul v-if="(data.advisor_top || []).length">
        <li v-for="a in data.advisor_top" :key="a.user_id">
          {{ a.name }} · 客户 {{ a.customers }} · score {{ a.score }}
        </li>
      </ul>
      <EmptyState v-else title="暂无顾问排行数据" />
    </template>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 10px; font-size: 1.05rem; }
h3 { margin: 14px 0 6px; font-size: 0.95rem; }
.grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.grid div {
  background: #f8fafc;
  border-radius: 8px;
  padding: 10px;
  display: grid;
}
.grid span { color: var(--muted); font-size: 12px; }
.grid strong { font-size: 1.3rem; }
ul { margin: 0; padding-left: 18px; }
@media (max-width: 700px) {
  .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
