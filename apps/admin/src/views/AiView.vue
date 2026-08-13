<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import EmptyState from '../components/EmptyState.vue'
import InsightCards from '../components/analytics/InsightCards.vue'
import MetricGlossary from '../components/analytics/MetricGlossary.vue'
import { useAuth } from '../composables/useAuth'
import {
  formatPercent,
  summarizeAdoption,
  type AdoptionRow,
} from '../utils/analyticsFormat'

const { api, role } = useAuth()
const adoption = ref<{ items?: AdoptionRow[]; group_by?: string } | null>(null)
const orgs = ref<any[]>([])
const error = ref('')
const loading = ref(true)
const groupBy = ref<'advisor' | 'day'>('advisor')
const fromDate = ref('')
const toDate = ref('')
const orgId = ref('' as string | number | '')

const rows = computed(() => adoption.value?.items || [])

const summary = computed(() => summarizeAdoption(rows.value))

const insightItems = computed(() => {
  const s = summary.value
  if (!rows.value.length) return []
  return [
    {
      key: 'rate',
      label: '当前筛选 · 采纳率',
      value: formatPercent(s.rate, 0),
      hint:
        s.rate == null
          ? '尚无「有用/不适用」反馈'
          : `有用 ${s.useful} · 不适用 ${s.reject}`,
    },
    {
      key: 'impressions',
      label: '建议曝光',
      value: String(s.impressions),
      hint: `复制到企微 ${s.copy} 次`,
    },
    {
      key: 'top',
      label: groupBy.value === 'day' ? '使用最多的顾问' : '最活跃顾问',
      value: s.topName || '—',
      hint: '按「有用 + 复制」合计粗排',
    },
  ]
})

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
    <h2>AI 使用分析</h2>
    <p class="lead muted">看顾问是否真的在用建议：复制、标记有用、不适用。</p>

    <form class="filters" @submit.prevent="load">
      <label>
        怎么看
        <select v-model="groupBy">
          <option value="advisor">按顾问汇总</option>
          <option value="day">按日下钻</option>
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
    <EmptyState
      v-else-if="!rows.length"
      title="暂无采纳数据"
      hint="请顾问在侧栏对建议点「复制到企微」或「标记有用/不适用」后再看；空库可先 seed 演示数据。"
    />
    <template v-else>
      <InsightCards :items="insightItems" />

      <table class="data">
        <thead>
          <tr>
            <th v-if="groupBy === 'day'">日期</th>
            <th>顾问</th>
            <th>曝光</th>
            <th>复制到企微</th>
            <th>标记有用</th>
            <th>编辑后有用</th>
            <th>不适用</th>
            <th>标签确认</th>
            <th>标签拒绝</th>
            <th>采纳率</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in rows" :key="i">
            <td v-if="groupBy === 'day'">{{ row.day || '—' }}</td>
            <td>{{ row.name }}</td>
            <td>{{ row.impressions }}</td>
            <td>{{ row.copy }}</td>
            <td>{{ row.adopt }}</td>
            <td>{{ row.edit_adopt }}</td>
            <td>{{ row.reject }}</td>
            <td>{{ row.tag_confirm }}</td>
            <td>{{ row.tag_reject }}</td>
            <td>{{ formatPercent(row.adoption_rate, 0) }}</td>
          </tr>
        </tbody>
      </table>

      <MetricGlossary />
    </template>
  </section>
</template>

<style scoped>
h2 {
  margin: 0 0 4px;
  font-size: 1.05rem;
}
.lead {
  margin: 0 0 12px;
  font-size: 13px;
}
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
.muted {
  color: var(--muted);
}
</style>
