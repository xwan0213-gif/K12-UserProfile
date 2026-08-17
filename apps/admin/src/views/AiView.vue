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
  <section class="rounded-panel border border-line bg-white p-5 shadow-soft">
    <div class="mb-4">
      <h2 class="font-display text-lg font-semibold">AI 使用分析</h2>
      <p class="mt-1 text-sm text-muted">看顾问是否真的在用建议：复制、标记有用、不适用。</p>
    </div>

    <form class="mb-4 flex flex-wrap items-end gap-2" @submit.prevent="load">
      <label class="grid gap-1 text-xs text-muted">
        怎么看
        <select v-model="groupBy" class="rounded-control border border-line px-2.5 py-1.5 text-sm">
          <option value="advisor">按顾问汇总</option>
          <option value="day">按日下钻</option>
        </select>
      </label>
      <label class="grid gap-1 text-xs text-muted">
        从
        <input v-model="fromDate" type="date" class="rounded-control border border-line px-2.5 py-1.5 text-sm" />
      </label>
      <label class="grid gap-1 text-xs text-muted">
        到
        <input v-model="toDate" type="date" class="rounded-control border border-line px-2.5 py-1.5 text-sm" />
      </label>
      <label v-if="role === 'admin'" class="grid gap-1 text-xs text-muted">
        组织
        <select v-model="orgId" class="rounded-control border border-line px-2.5 py-1.5 text-sm">
          <option value="">全部</option>
          <option v-for="o in orgs" :key="o.id" :value="o.id">{{ o.name }}</option>
        </select>
      </label>
      <button type="submit" class="rounded-control bg-fjord px-3 py-1.5 text-sm font-semibold text-white">
        查询
      </button>
    </form>

    <p v-if="loading" class="text-sm text-muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <EmptyState
      v-else-if="!rows.length"
      title="暂无采纳数据"
      hint="请顾问在侧栏对建议点「复制到企微」或「标记有用/不适用」后再看；空库可先 seed 演示数据。"
    />
    <template v-else>
      <InsightCards :items="insightItems" />

      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="border-b border-line text-muted">
            <tr>
              <th v-if="groupBy === 'day'" class="pb-2 pr-3 font-medium">日期</th>
              <th class="pb-2 pr-3 font-medium">顾问</th>
              <th class="pb-2 pr-3 font-medium">曝光</th>
              <th class="pb-2 pr-3 font-medium">复制到企微</th>
              <th class="pb-2 pr-3 font-medium">标记有用</th>
              <th class="pb-2 pr-3 font-medium">编辑后有用</th>
              <th class="pb-2 pr-3 font-medium">不适用</th>
              <th class="pb-2 pr-3 font-medium">标签确认</th>
              <th class="pb-2 pr-3 font-medium">标签拒绝</th>
              <th class="pb-2 font-medium">采纳率</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, i) in rows"
              :key="i"
              class="border-b border-line/60 hover:bg-fjord-soft/40"
            >
              <td v-if="groupBy === 'day'" class="py-2 pr-3">{{ row.day || '—' }}</td>
              <td class="py-2 pr-3">{{ row.name }}</td>
              <td class="py-2 pr-3">{{ row.impressions }}</td>
              <td class="py-2 pr-3">{{ row.copy }}</td>
              <td class="py-2 pr-3">{{ row.adopt }}</td>
              <td class="py-2 pr-3">{{ row.edit_adopt }}</td>
              <td class="py-2 pr-3">{{ row.reject }}</td>
              <td class="py-2 pr-3">{{ row.tag_confirm }}</td>
              <td class="py-2 pr-3">{{ row.tag_reject }}</td>
              <td class="py-2">{{ formatPercent(row.adoption_rate, 0) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <MetricGlossary />
    </template>
  </section>
</template>
