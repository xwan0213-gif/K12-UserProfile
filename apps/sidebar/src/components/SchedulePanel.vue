<script setup lang="ts">
import { computed, onMounted, ref, shallowRef, watch } from 'vue'
import type { ApiFn } from '../composables/useApi'
import ScheduleCreateForm from './schedule/ScheduleCreateForm.vue'
import ScheduleDraftCard from './schedule/ScheduleDraftCard.vue'
import ScheduleItemRow from './schedule/ScheduleItemRow.vue'
import SchedulePrefForm from './schedule/SchedulePrefForm.vue'
import type { RemindPref, ScheduleDraft, ScheduleEdits, ScheduleItem } from './schedule/types'

const props = defineProps<{
  api: ApiFn
  customerId: number | null
}>()

const emit = defineEmits<{ status: [msg: string] }>()

const items = ref<ScheduleItem[]>([])
const drafts = ref<ScheduleDraft[]>([])
const busy = shallowRef(false)
const actionBusy = shallowRef(false)
const prefOpen = shallowRef(false)
const pref = ref<RemindPref>({})
const filter = ref<'today' | 'week' | 'all'>('week')
const createSavedTick = shallowRef(0)

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
  if (!props.customerId) {
    items.value = []
    drafts.value = []
    return
  }
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
    for (let i = 0; i < 40; i++) {
      await load()
      if (drafts.value.length) break
      await new Promise((r) => setTimeout(r, 800))
    }
    emit('status', drafts.value.length ? '已收到日程草稿' : '日程建议生成中，请稍后刷新')
  } catch (e: any) {
    emit('status', e?.message || '日程建议失败')
  } finally {
    busy.value = false
  }
}

async function createItem(payload: {
  title: string
  start_at: string | null
  priority: string
  remark: string | null
  sync_calendar: boolean
}) {
  if (!props.customerId) return
  actionBusy.value = true
  try {
    const item = await props.api('/sidebar/schedules', {
      method: 'POST',
      body: JSON.stringify({
        customer_id: props.customerId,
        title: payload.title,
        start_at: payload.start_at,
        priority: payload.priority,
        remark: payload.remark,
        sync_calendar: payload.sync_calendar,
      }),
    })
    createSavedTick.value += 1
    emit(
      'status',
      item?.sync_state === 'failed'
        ? '已创建站内待办（日历同步失败，已降级）'
        : '已创建待办',
    )
    await load()
  } catch (e: any) {
    emit('status', e?.message || '创建待办失败')
  } finally {
    actionBusy.value = false
  }
}

async function patchItem(id: number, body: Record<string, unknown>) {
  actionBusy.value = true
  try {
    await props.api(`/sidebar/schedules/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    })
    const st = body.status
    emit(
      'status',
      st === 'done' ? '已标记完成' : st === 'cancelled' ? '已取消待办' : '已更新待办',
    )
    await load()
  } catch (e: any) {
    emit('status', e?.message || '更新待办失败')
  } finally {
    actionBusy.value = false
  }
}

async function confirmDraft(
  suggestionId: number,
  syncCalendar: boolean,
  edits: ScheduleEdits,
) {
  actionBusy.value = true
  try {
    const item = await props.api('/sidebar/schedules/confirm', {
      method: 'POST',
      body: JSON.stringify({
        suggestion_id: suggestionId,
        sync_calendar: syncCalendar,
        edits: {
          title: edits.title,
          start_at: edits.start_at,
          priority: edits.priority,
          remark: edits.remark,
        },
      }),
    })
    emit(
      'status',
      item?.sync_state === 'failed'
        ? '已确认站内待办（日历同步失败，已降级）'
        : '已确认日程',
    )
    await load()
  } catch (e: any) {
    emit('status', e?.message || '确认失败')
  } finally {
    actionBusy.value = false
  }
}

async function dismissDraft(suggestionId: number) {
  actionBusy.value = true
  try {
    await props.api('/sidebar/schedules/dismiss', {
      method: 'POST',
      body: JSON.stringify({ suggestion_id: suggestionId }),
    })
    emit('status', '已忽略该草稿')
    await load()
  } catch (e: any) {
    emit('status', e?.message || '忽略失败')
  } finally {
    actionBusy.value = false
  }
}

async function remind(id: number, mode: 'weak' | 'strong') {
  const tip =
    mode === 'weak'
      ? '将向侧栏推送弱提示（需已开启「侧边栏弱提示」偏好，且 SSE 已连接）。继续？'
      : '将尝试企微强提醒；无权限或未接入时会降级，仅记录日志，不会代发客户消息。继续？'
  if (!window.confirm(tip)) return
  actionBusy.value = true
  try {
    const res = await props.api(`/sidebar/schedules/${id}/remind`, {
      method: 'POST',
      body: JSON.stringify({ mode }),
    })
    const parts = [res?.message || (mode === 'weak' ? '弱提醒已处理' : '强提醒已处理')]
    if (res?.degraded) parts.push('已降级')
    if (res?.delivered === false && !res?.degraded) parts.push('未投递')
    emit('status', parts.join(' · '))
  } catch (e: any) {
    emit('status', e?.message || '提醒失败')
  } finally {
    actionBusy.value = false
  }
}

async function savePref(next: RemindPref) {
  try {
    pref.value = await props.api('/sidebar/schedules/pref', {
      method: 'PATCH',
      body: JSON.stringify({
        weak_tip: next.weak_tip !== false,
        strong_notify: next.strong_notify !== false,
        quiet_hours: next.quiet_hours || [],
      }),
    })
    emit('status', '提醒偏好已保存')
    prefOpen.value = false
  } catch (e: any) {
    emit('status', e?.message || '保存偏好失败')
  }
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

defineExpose({ load, suggest })
</script>

<template>
  <section class="panel">
    <div class="title-row">
      <h2>日程 <em class="ai-badge">AI 建议</em></h2>
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

    <SchedulePrefForm
      :pref="pref"
      :open="prefOpen"
      @update:open="(v) => (prefOpen = v)"
      @save="savePref"
    />

    <ScheduleCreateForm
      :disabled="!customerId || actionBusy"
      :saved-tick="createSavedTick"
      @create="createItem"
    />

    <h3>待办列表</h3>
    <ul v-if="filteredItems.length" class="list">
      <ScheduleItemRow
        v-for="it in filteredItems"
        :key="it.id"
        :item="it"
        :busy="actionBusy"
        @patch="patchItem"
        @remind="remind"
      />
    </ul>
    <p v-else class="empty-hint">暂无已确认待办。可手工新建，或确认下方 AI 草稿。</p>

    <h3>★ AI 识别待确认</h3>
    <ScheduleDraftCard
      v-for="d in drafts"
      :key="d.suggestion_id"
      :draft="d"
      :busy="actionBusy"
      @confirm="confirmDraft"
      @dismiss="dismissDraft"
    />
    <p v-if="!drafts.length" class="empty-hint">
      暂无草稿。可点「AI 识别待办」，或从会话点「生成日程（全会话）」。
    </p>
  </section>
</template>

<style scoped>
.panel { padding: 4px 0; }
.title-row, .filters {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.title-row { margin-bottom: 8px; }
h2 { margin: 0; font-size: 1.05rem; }
h3 { margin: 12px 0 6px; font-size: 0.95rem; }
.list { list-style: none; padding: 0; margin: 0; }
</style>
