<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { ApiFn } from '../composables/useApi'

const props = defineProps<{
  api: ApiFn
  customerId: number | null
}>()

const emit = defineEmits<{ status: [msg: string] }>()

type ScheduleItem = {
  id: number
  title: string
  start_at?: string | null
  priority?: string
  sync_state?: string
  status?: string
  remark?: string | null
}

type ScheduleDraft = {
  suggestion_id: number
  title?: string
  time_text?: string
  start_at?: string | null
  priority?: string
  source_quote?: string
  predictive_tip?: string
}

const items = ref<ScheduleItem[]>([])
const drafts = ref<ScheduleDraft[]>([])
const busy = ref(false)
const prefOpen = ref(false)
const pref = ref<{ weak_tip?: boolean; strong_notify?: boolean; quiet_hours?: string[] }>({})
const filter = ref<'today' | 'week' | 'all'>('week')

const filteredItems = computed(() => {
  const list = items.value
  if (filter.value === 'all') return list
  const now = new Date()
  const start = new Date(now)
  start.setHours(0, 0, 0, 0)
  const end = new Date(start)
  if (filter.value === 'today') end.setDate(end.getDate() + 1)
  else end.setDate(end.getDate() + 7)
  return list.filter((it) => {
    if (!it.start_at) return filter.value === 'week'
    const t = new Date(it.start_at)
    return t >= start && t < end
  })
})

async function load() {
  if (!props.customerId) return
  const data = await props.api(
    `/sidebar/schedules?customer_id=${props.customerId}&scope=customer`,
  )
  items.value = data?.items || []
  drafts.value = data?.drafts || []
}

async function loadPref() {
  const raw = (await props.api('/sidebar/schedules/pref')) || {}
  pref.value = {
    weak_tip: raw.weak_tip !== false,
    strong_notify: raw.strong_notify !== false,
    quiet_hours: raw.quiet_hours || [],
  }
}

async function suggest() {
  if (!props.customerId) return
  busy.value = true
  emit('status', '生成日程建议…')
  try {
    await props.api('/sidebar/schedules/suggest', {
      method: 'POST',
      body: JSON.stringify({ customer_id: props.customerId, force: true }),
    })
    // poll briefly for draft
    for (let i = 0; i < 40; i++) {
      await load()
      if (drafts.value.length) break
      await new Promise((r) => setTimeout(r, 800))
    }
    emit('status', drafts.value.length ? '已收到日程草稿' : '日程建议生成中，请稍后刷新')
  } finally {
    busy.value = false
  }
}

async function confirmDraft(d: ScheduleDraft, syncCalendar = false) {
  const item = await props.api('/sidebar/schedules/confirm', {
    method: 'POST',
    body: JSON.stringify({
      suggestion_id: d.suggestion_id,
      sync_calendar: syncCalendar,
    }),
  })
  emit(
    'status',
    item?.sync_state === 'failed'
      ? '已确认站内待办（日历同步失败，已降级）'
      : '已确认日程',
  )
  await load()
}

async function remind(id: number, mode: 'weak' | 'strong') {
  const res = await props.api(`/sidebar/schedules/${id}/remind`, {
    method: 'POST',
    body: JSON.stringify({ mode }),
  })
  emit('status', res?.message || (mode === 'weak' ? '弱提醒已触发' : '强提醒已处理'))
}

async function savePref() {
  pref.value = await props.api('/sidebar/schedules/pref', {
    method: 'PATCH',
    body: JSON.stringify({
      weak_tip: pref.value.weak_tip !== false,
      strong_notify: pref.value.strong_notify !== false,
      quiet_hours: pref.value.quiet_hours || [],
    }),
  })
  emit('status', '提醒偏好已保存')
  prefOpen.value = false
}

function priorityLabel(p?: string) {
  if (p === 'high') return '高'
  if (p === 'low') return '低'
  return '中'
}

function syncLabel(s?: string) {
  if (s === 'synced') return '已同步企微日历'
  if (s === 'failed') return '日历同步失败（站内保留）'
  if (s === 'pending') return '同步中'
  return '仅站内'
}

watch(
  () => props.customerId,
  () => {
    void load()
  },
)

onMounted(() => {
  void load()
  void loadPref()
})

defineExpose({ load })
</script>

<template>
  <section class="card">
    <div class="title-row">
      <h2>日程 <em class="ai">AI 建议</em></h2>
      <div class="filters">
        <button type="button" :class="{ active: filter === 'today' }" @click="filter = 'today'">今日</button>
        <button type="button" :class="{ active: filter === 'week' }" @click="filter = 'week'">本周</button>
        <button type="button" :class="{ active: filter === 'all' }" @click="filter = 'all'">全部</button>
      </div>
      <button type="button" :disabled="busy || !customerId" @click="suggest">
        {{ busy ? '生成中…' : 'AI 识别待办' }}
      </button>
      <button type="button" @click="prefOpen = !prefOpen">提醒偏好</button>
    </div>

    <div v-if="prefOpen" class="pref block">
      <label>
        <input v-model="pref.weak_tip" type="checkbox" :true-value="true" :false-value="false" />
        侧边栏弱提示
      </label>
      <label>
        <input v-model="pref.strong_notify" type="checkbox" :true-value="true" :false-value="false" />
        高优强提醒（企微，可降级）
      </label>
      <button type="button" class="primary" @click="savePref">保存偏好</button>
    </div>

    <h3>待办列表</h3>
    <ul v-if="filteredItems.length" class="list">
      <li v-for="it in filteredItems" :key="it.id">
        <div>
          <strong>{{ it.title }}</strong>
          <p class="muted">
            {{ it.start_at ? it.start_at.replace('T', ' ').replace('Z', '') : '时间待定' }}
            · {{ priorityLabel(it.priority) }}
            · {{ syncLabel(it.sync_state) }}
          </p>
        </div>
        <div class="actions">
          <button type="button" @click="remind(it.id, 'weak')">弱</button>
          <button type="button" @click="remind(it.id, 'strong')">强</button>
        </div>
      </li>
    </ul>
    <p v-else class="muted">暂无已确认待办。</p>

    <h3>★ AI 识别待确认</h3>
    <div v-for="d in drafts" :key="d.suggestion_id" class="block draft">
      <p>
        「{{ d.source_quote || d.title }}」→ 建议：<strong>{{ d.title }}</strong>
      </p>
      <p class="muted">
        时间：{{ d.time_text || '待定' }}
        · 优先级 {{ priorityLabel(d.priority) }}
      </p>
      <p v-if="d.predictive_tip" class="muted">预测：{{ d.predictive_tip }}</p>
      <div class="actions">
        <button type="button" class="primary" @click="confirmDraft(d, false)">确认</button>
        <button type="button" @click="confirmDraft(d, true)">确认并同步日历</button>
      </div>
    </div>
    <p v-if="!drafts.length" class="muted">暂无草稿。可点「AI 识别待办」或写入含时间意图的聊天后生成。</p>
  </section>
</template>

<style scoped>
.card {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #e4e7ec;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 12px;
}
.title-row, .actions, .filters {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.title-row { margin-bottom: 8px; }
h2 { margin: 0; font-size: 1.05rem; }
h3 { margin: 12px 0 6px; font-size: 0.95rem; }
.muted { color: #667085; margin: 4px 0; }
.ai { color: #6941c6; font-style: normal; font-size: 12px; margin-left: 6px; }
.list { list-style: none; padding: 0; margin: 0; }
.list li {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #eef2f6;
}
.block { margin: 10px 0; }
.draft {
  background: #f8fafc;
  border: 1px solid #e4e7ec;
  border-radius: 8px;
  padding: 10px;
}
.pref label { display: flex; gap: 6px; align-items: center; margin: 6px 0; }
button {
  border: 1px solid #d0d5dd;
  background: #fff;
  border-radius: 8px;
  padding: 6px 10px;
  cursor: pointer;
}
button.primary { background: #175cd3; color: #fff; border-color: #175cd3; }
button.active { background: #1f2a37; color: #fff; }
button:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
