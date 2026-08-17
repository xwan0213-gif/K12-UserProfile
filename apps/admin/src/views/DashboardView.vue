<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import EmptyState from '../components/EmptyState.vue'
import AdvisorRankList from '../components/analytics/AdvisorRankList.vue'
import FunnelBars from '../components/analytics/FunnelBars.vue'
import InsightCards from '../components/analytics/InsightCards.vue'
import MetricGlossary from '../components/analytics/MetricGlossary.vue'
import { useAuth } from '../composables/useAuth'
import { formatPercent, formatWowDelta, wowTone } from '../utils/analyticsFormat'

const { api, role } = useAuth()
const data = ref<any>(null)
const error = ref('')
const loading = ref(true)

const insightItems = computed(() => {
  const pulse = data.value?.ai_pulse
  if (!pulse) return []
  const thisP = pulse.this_period || {}
  const tone = wowTone(pulse.wow_delta)
  const top = pulse.top_advisor
  return [
    {
      key: 'rate',
      label: '近 7 日建议采纳率',
      value: formatPercent(thisP.adoption_rate, 0),
      hint:
        thisP.adoption_rate == null
          ? '顾问尚未标记「有用/不适用」'
          : `有用 ${thisP.useful || 0} · 不适用 ${thisP.reject || 0}`,
    },
    {
      key: 'wow',
      label: '较前 7 日',
      value: formatWowDelta(pulse.wow_delta),
      hint:
        pulse.prev_period?.adoption_rate == null
          ? '上期无反馈，暂不对比'
          : `上期 ${formatPercent(pulse.prev_period.adoption_rate, 0)}`,
      tone,
    },
    {
      key: 'top',
      label: '近 7 日最活跃顾问',
      value: top?.name || '暂无',
      hint: top
        ? `AI 使用 ${top.week_actions} 次（复制/有用/不适用等）`
        : '暂无侧栏反馈埋点',
    },
  ]
})

const emptyFunnel = computed(() => {
  const f = data.value?.funnel
  if (!f) return true
  return !(f.lead || f.intent || f.trial || f.deal)
})

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
  <section class="rounded-panel border border-line bg-white p-5 shadow-soft">
    <div class="mb-4">
      <h2 class="font-display text-lg font-semibold">经营看板</h2>
      <p class="mt-1 text-sm text-muted">先看结论，再下钻漏斗与顾问人效。</p>
    </div>

    <p v-if="loading" class="text-sm text-muted">加载中…</p>
    <EmptyState
      v-else-if="error"
      :title="error"
      hint="若无权限或会话过期，请重新登录。"
    />
    <template v-else-if="data">
      <InsightCards v-if="insightItems.length" :items="insightItems" />
      <p v-else-if="role === 'advisor'" class="mb-3 text-sm text-muted">
        顾问视角：下方为您可见范围内的客户漏斗；团队 AI 采纳请联系主管查看「AI 分析」。
      </p>

      <h3 class="mb-2 mt-4 font-display text-base font-semibold">转化漏斗</h3>
      <EmptyState
        v-if="emptyFunnel"
        title="暂无漏斗数据"
        hint="可见范围内还没有客户，或尚未 seed 演示数据。"
      />
      <FunnelBars v-else :funnel="data.funnel" :labels="data.funnel_labels" />

      <p class="mt-3.5 text-sm">
        续费率（参考）
        <strong class="ml-1">{{ formatPercent(data.renewal_rate, 0) }}</strong>
        <span class="text-muted"> · {{ data.renewal_note }}</span>
      </p>

      <h3 class="mb-2 mt-4 font-display text-base font-semibold">顾问人效 Top</h3>
      <EmptyState
        v-if="!(data.advisor_top || []).length"
        title="暂无顾问排行"
        hint="范围内没有启用顾问，或尚未分配客户。"
      />
      <AdvisorRankList v-else :items="data.advisor_top" />

      <MetricGlossary />
    </template>
  </section>
</template>
