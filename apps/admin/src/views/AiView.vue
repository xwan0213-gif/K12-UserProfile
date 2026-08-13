<script setup lang="ts">
import { onMounted, ref } from 'vue'
import EmptyState from '../components/EmptyState.vue'
import { useAuth } from '../composables/useAuth'

const { api, role } = useAuth()
const adoption = ref<any>(null)
const orgs = ref<any[]>([])
const error = ref('')
const loading = ref(true)
const groupBy = ref<'advisor' | 'day'>('advisor')
const fromDate = ref('')
const toDate = ref('')
const orgId = ref('' as string | number | '')

async function loadOrgs() {
  if (role.value !== 'admin') return
  try {
    const data = await api('/admin/orgs')
    orgs.value = data?.items || []
  } catch {
    orgs.value = []
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const qs = new URLSearchParams({ group_by: groupBy.value })
    if (fromDate.value) qs.set('from', `${fromDate.value}T00:00:00`)
    if (toDate.value) qs.set('to', `${toDate.value}T23:59:59`)
    if (role.value === 'admin' && orgId.value !== '') {
      qs.set('org_id', String(orgId.value))
    }
    adoption.value = await api(`/admin/ai/adoption?${qs}`)
  } catch (e: any) {
    error.value = e?.message || '加载失败（AI 分析仅管理员/区域主管可见）'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadOrgs()
  await load()
})
</script>

<template>
  <section class="card">
    <h2>AI 使用分析（采纳率）</h2>

    <form class="filters" @submit.prevent="load">
      <label>
        聚合
        <select v-model="groupBy">
          <option value="advisor">按顾问</option>
          <option value="day">按日</option>
        </select>
      </label>
      <label>
        从
        <input v-model="fromDate" type="date" />
      </label>
      <label>
        到
        <input v-model="toDate" type="date" />
      </label>
      <label v-if="role === 'admin'">
        组织
        <select v-model="orgId">
          <option value="">全部</option>
          <option v-for="o in orgs" :key="o.id" :value="o.id">{{ o.name }}</option>
        </select>
      </label>
      <button type="submit" class="primary">查询</button>
    </form>

    <p v-if="loading" class="muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <EmptyState v-else-if="!(adoption?.items || []).length" title="暂无采纳数据" />
    <table v-else class="data">
      <thead>
        <tr>
          <th v-if="groupBy === 'day'">日期</th>
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
          <td v-if="groupBy === 'day'">{{ row.day || '—' }}</td>
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
    <p class="muted tip">口径来自 event_log；支持 from/to 与 group_by=day。</p>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 10px; font-size: 1.05rem; }
.filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: end;
  margin-bottom: 12px;
}
.filters label {
  display: grid;
  gap: 4px;
  font-size: 12px;
  color: var(--muted);
}
.filters input,
.filters select {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 8px;
  color: var(--ink);
}
.tip { margin-top: 10px; }
</style>
