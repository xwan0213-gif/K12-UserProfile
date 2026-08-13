<script setup lang="ts">
import { onMounted, ref } from 'vue'
import EmptyState from '../components/EmptyState.vue'
import { useAuth } from '../composables/useAuth'

const { api } = useAuth()
const adoption = ref<any>(null)
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    adoption.value = await api('/admin/ai/adoption?group_by=advisor')
  } catch (e: any) {
    error.value = e?.message || '加载失败（AI 分析仅管理员/区域主管可见）'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="card">
    <h2>AI 使用分析（采纳率）</h2>
    <p v-if="loading" class="muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <EmptyState v-else-if="!(adoption?.items || []).length" title="暂无采纳数据" />
    <table v-else class="data">
      <thead>
        <tr>
          <th>顾问</th>
          <th>曝光</th>
          <th>复制</th>
          <th>采纳</th>
          <th>编辑采纳</th>
          <th>拒绝</th>
          <th>标签确认</th>
          <th>标签拒绝</th>
          <th>采纳率</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, i) in adoption.items" :key="i">
          <td>{{ row.name }}</td>
          <td>{{ row.impressions }}</td>
          <td>{{ row.copy }}</td>
          <td>{{ row.adopt }}</td>
          <td>{{ row.edit_adopt }}</td>
          <td>{{ row.reject }}</td>
          <td>{{ row.tag_confirm }}</td>
          <td>{{ row.tag_reject }}</td>
          <td>{{ row.adoption_rate ?? '—' }}</td>
        </tr>
      </tbody>
    </table>
    <p class="muted tip">口径来自 event_log；按日/区间下钻属阶段 D.6。</p>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 10px; font-size: 1.05rem; }
.tip { margin-top: 10px; }
</style>
