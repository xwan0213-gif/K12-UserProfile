<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { Calendar, LogOut, MessageSquare, Tags, User } from '@lucide/vue'
import CapabilityBar from './components/CapabilityBar.vue'
import CustomerHeader from './components/CustomerHeader.vue'
import ChatPanel from './components/chat/ChatPanel.vue'
import LoginView from './components/LoginView.vue'
import ProfilePanel from './components/profile/ProfilePanel.vue'
import SuggestPanel from './components/suggest/SuggestPanel.vue'
import type { ReplyOutcome } from './components/suggest/SuggestPanel.vue'
import TagsPanel from './components/tags/TagsPanel.vue'
import SchedulePanel from './components/SchedulePanel.vue'
import WeakTipBar from './components/WeakTipBar.vue'
import AppToast from './components/shell/AppToast.vue'
import UiIcon from './components/UiIcon.vue'
import { useAuth } from './composables/useAuth'
import { createSseClient } from './composables/useSse'
import { useToast } from './composables/useToast'

const { api, token, me, status: authStatus, loggedIn, logout, bootSession, setToken } = useAuth()

const ready = ref(false)
const status = ref('idle')
const customerId = ref<number | null>(null)
const externalUserId = ref('demo_wang')
const tab = ref<'profile' | 'tags' | 'suggest' | 'schedule'>('profile')
const showChat = ref(true)
const aiStale = ref(false)
const context = ref<any>(null)
const profile = ref<any>(null)
const tags = ref<any>(null)
const reply = ref<any>(null)
const replyScene = ref<'sales' | 'cs'>('sales')
const replyBusy = ref(false)
const replyOutcome = ref<ReplyOutcome | null>(null)
const tagRecommendBusy = ref(false)
const lastAsr = ref<string | null>(null)
const customers = ref<any[]>([])
const sseLog = ref('')
const weakTip = ref<{ text: string; priority?: string } | null>(null)
const schedulePanel = ref<{
  load: () => Promise<void>
  suggest: () => Promise<void>
} | null>(null)
const chatPanel = ref<{ load: () => Promise<void> } | null>(null)
const healthFlags = ref({
  mockWecom: true,
  mockLlm: false,
  llmProvider: 'deepseek',
  asr: 'Fake',
  calendar: '降级',
  calendarHint: '企微日历未接入',
})
const demoOpen = ref(false)

const toast = useToast()
const generating = computed(() => !!profile.value?.generating)

const tabs = [
  { id: 'profile' as const, label: '画像', icon: User },
  { id: 'tags' as const, label: '标签', icon: Tags },
  { id: 'suggest' as const, label: '建议', icon: MessageSquare },
  { id: 'schedule' as const, label: '日程', icon: Calendar },
]

function notify(msg: string, kind: 'info' | 'ok' | 'warn' | 'err' = 'info') {
  status.value = msg
  toast.push(msg, kind)
}

const sse = createSseClient({
  getToken: () => token.value,
  getCustomerId: () => customerId.value,
  onStatus: (msg) => {
    status.value = msg
  },
  onEvent: async (ev, data) => {
    sseLog.value = `${ev}: ${data}`
    if (ev === 'weak_tip') {
      try {
        const payload = JSON.parse(data || '{}')
        weakTip.value = {
          text: payload.text || '日程提醒',
          priority: payload.priority,
        }
        notify('收到弱提醒', 'warn')
      } catch {
        weakTip.value = { text: data || '日程提醒' }
        notify('收到弱提醒', 'warn')
      }
      return
    }
    if (
      ev === 'profile_draft' ||
      ev === 'job_failed' ||
      ev === 'reply_ready' ||
      ev === 'tag_recommend' ||
      ev === 'schedule_draft'
    ) {
      if (ev === 'reply_ready') tab.value = 'suggest'
      if (ev === 'tag_recommend') tab.value = 'tags'
      if (ev === 'schedule_draft') tab.value = 'schedule'
      if (ev === 'profile_draft') tab.value = 'profile'
      await refreshAll()
      if (ev === 'schedule_draft') await schedulePanel.value?.load()
      const msg =
        ev === 'profile_draft'
          ? '收到画像草稿'
          : ev === 'reply_ready'
            ? '收到话术建议'
            : ev === 'tag_recommend'
              ? '收到标签推荐'
              : ev === 'schedule_draft'
                ? '收到日程草稿'
                : '生成失败'
      notify(msg, ev === 'job_failed' ? 'err' : 'ok')
    }
  },
})

async function loadHealth() {
  try {
    const res = await fetch('/health')
    const json = await res.json()
    const d = json?.data || json
    const calReady = d.calendar_mode === 'ready'
    healthFlags.value = {
      mockWecom: !!d.mock_wecom,
      mockLlm: !!d.mock_llm,
      llmProvider: d.llm_provider || 'deepseek',
      asr: d.asr_provider
        ? String(d.asr_provider).toLowerCase() === 'fake'
          ? 'Fake'
          : String(d.asr_provider)
        : d.mock_llm
          ? 'Fake'
          : 'Fake/Stub',
      calendar: calReady ? '可同步' : '降级',
      calendarHint: d.calendar_hint || (calReady ? '可尝试同步' : '企微日历未接入'),
    }
  } catch {
    /* ignore */
  }
}

async function loadCustomers() {
  const data = await api('/mock/customers')
  customers.value = data.items || []
}

async function enterWorkbench() {
  await loadCustomers()
  if (!customerId.value && customers.value.length) {
    customerId.value = customers.value[0].id
    const first = customers.value[0]
    if (first?.external_id) externalUserId.value = first.external_id
  }
  await refreshAll()
  sse.connect()
}

async function onLoggedIn() {
  ready.value = true
  notify(authStatus.value, 'ok')
  await enterWorkbench()
}

async function mockExchange() {
  status.value = '换票中…'
  try {
    const data = await api('/auth/wecom/exchange', {
      method: 'POST',
      body: JSON.stringify({
        code: 'mock_code',
        external_userid: externalUserId.value || undefined,
      }),
    })
    setToken(data.access_token)
    if (data.customer_id) customerId.value = data.customer_id
    notify(`演示换票：${data.user.name}`, 'ok')
    await loadCustomers()
    if (!customerId.value && customers.value.length) {
      customerId.value = customers.value[0].id
    }
    await refreshAll()
    sse.connect()
  } catch (e: any) {
    notify(String(e?.message || e), 'err')
  }
}

function onSelectCustomer(id: number) {
  customerId.value = id
  void switchCustomer()
}

async function switchCustomer() {
  if (!customerId.value) return
  const selected = customers.value.find((c) => c.id === customerId.value)
  if (selected?.external_id) externalUserId.value = selected.external_id
  replyOutcome.value = null
  notify(`已切换客户 #${customerId.value}`, 'info')
  await refreshAll()
  await chatPanel.value?.load()
  sse.connect()
}

async function refreshAll() {
  if (!customerId.value) return
  const q = `customer_id=${customerId.value}`
  context.value = await api(`/sidebar/context?${q}`)
  profile.value = await api(`/sidebar/profile?${q}`)
  tags.value = await api(`/sidebar/tags?${q}`)
  reply.value = await api(`/sidebar/reply/latest?${q}&scene=${replyScene.value}`)
  if (
    reply.value?.primary &&
    reply.value?.suggestion_id !== replyOutcome.value?.suggestionId
  ) {
    replyOutcome.value = null
  }
  if (tab.value === 'schedule') await schedulePanel.value?.load()
}

function onChatStale() {
  aiStale.value = true
}

async function onSceneChange(scene: 'sales' | 'cs') {
  replyScene.value = scene
  replyOutcome.value = null
  await refreshAll()
}

async function suggestReply() {
  if (!customerId.value) return
  aiStale.value = false
  replyBusy.value = true
  replyOutcome.value = null
  status.value = '生成话术建议…'
  const prevId = reply.value?.suggestion_id ?? null
  try {
    await api('/sidebar/reply/suggest', {
      method: 'POST',
      body: JSON.stringify({
        customer_id: customerId.value,
        scene: replyScene.value,
        force: true,
      }),
    })
    for (let i = 0; i < 40; i++) {
      reply.value = await api(
        `/sidebar/reply/latest?customer_id=${customerId.value}&scene=${replyScene.value}`,
      )
      const nextId = reply.value?.suggestion_id
      // 必须等新 suggestion，不能把旧话术当成「已生成完成」
      if (nextId != null && nextId !== prevId && reply.value?.primary) break
      await new Promise((r) => setTimeout(r, 800))
    }
    if (reply.value?.based_on_asr) lastAsr.value = reply.value.based_on_asr
    const fresh =
      reply.value?.suggestion_id != null && reply.value.suggestion_id !== prevId
    notify(
      fresh && reply.value?.primary ? '已生成话术建议' : '话术生成中，请稍后查看',
      fresh && reply.value?.primary ? 'ok' : 'info',
    )
  } finally {
    replyBusy.value = false
  }
}

async function replyFeedback(
  action: 'copy' | 'adopt' | 'reject' | 'edit_adopt',
  text?: string,
) {
  if (!reply.value?.suggestion_id) return
  const suggestionId = reply.value.suggestion_id as number
  const payloadText =
    (text || '').trim() ||
    (typeof reply.value.primary === 'string' ? reply.value.primary : '')

  if (action === 'copy' && payloadText) {
    try {
      await navigator.clipboard.writeText(payloadText)
    } catch {
      /* ignore */
    }
  }

  await api('/sidebar/reply/feedback', {
    method: 'POST',
    body: JSON.stringify({
      suggestion_id: suggestionId,
      action,
      edited_content: action === 'edit_adopt' ? payloadText : undefined,
    }),
  })

  if (action === 'copy') {
    replyOutcome.value = {
      kind: 'copied',
      text: payloadText,
      suggestionId,
    }
    notify('已复制（请到企微手动发送，系统不代发）', 'ok')
    return
  }

  const kindMap = {
    adopt: 'adopted',
    reject: 'rejected',
    edit_adopt: 'edit_adopted',
  } as const

  replyOutcome.value = {
    kind: kindMap[action],
    text: action === 'reject' ? payloadText || undefined : payloadText,
    suggestionId,
  }
  notify(
    action === 'reject'
      ? '已标记不适用（不会代发）'
      : action === 'edit_adopt'
        ? '已按编辑稿标记有用（不会代发）'
        : '已标记有用（不会代发）',
    action === 'reject' ? 'warn' : 'ok',
  )

  reply.value = await api(
    `/sidebar/reply/latest?customer_id=${customerId.value}&scene=${replyScene.value}`,
  )
}

function clearReplyOutcome() {
  replyOutcome.value = null
}

async function recommendTags() {
  if (!customerId.value || tagRecommendBusy.value) return
  aiStale.value = false
  tagRecommendBusy.value = true
  status.value = '生成标签推荐…'
  const prevId = tags.value?.recommendations?.suggestion_id ?? null
  try {
    await api('/sidebar/tags/recommend', {
      method: 'POST',
      body: JSON.stringify({ customer_id: customerId.value, force: true }),
    })
    for (let i = 0; i < 40; i++) {
      tags.value = await api(`/sidebar/tags?customer_id=${customerId.value}`)
      const nextId = tags.value?.recommendations?.suggestion_id
      if (nextId != null && nextId !== prevId) break
      await new Promise((r) => setTimeout(r, 800))
    }
    const fresh =
      tags.value?.recommendations?.suggestion_id != null &&
      tags.value.recommendations.suggestion_id !== prevId
    status.value = fresh ? '已收到标签推荐' : '标签推荐生成中，请稍后刷新'
    notify(status.value, fresh ? 'ok' : 'info')
  } catch (e: any) {
    notify(e?.message || '标签推荐失败', 'err')
  } finally {
    tagRecommendBusy.value = false
  }
}

async function refreshTags() {
  if (!customerId.value) return
  tags.value = await api(`/sidebar/tags?customer_id=${customerId.value}`)
  context.value = await api(`/sidebar/context?customer_id=${customerId.value}`)
}

async function seedPhysicsScenario() {
  status.value = '写入物理场景…'
  const data = await api('/mock/seed/scenario', {
    method: 'POST',
    body: JSON.stringify({
      external_id: 'demo_physics',
      parent_name: '赵女士',
      student_name: '赵一凡',
      grade: '高一',
      school: '市一中',
      stage: 'senior',
      append_messages: false,
      cs_summary: '关注高一物理一对一，价格敏感。',
      messages: [
        { direction: 'in', content: '孩子高一物理跟不上，想问有没有一对一' },
        { direction: 'out', content: '方便说下最近考试分数吗？' },
        { direction: 'in', content: '期中物理 58，想先试听，价格别太贵' },
      ],
    }),
  })
  await loadCustomers()
  customerId.value = data.customer_id
  externalUserId.value = data.external_id || 'demo_physics'
  notify(`场景就绪：客户 #${data.customer_id}`, 'ok')
  await refreshAll()
  await chatPanel.value?.load()
  sse.connect()
}

async function generate() {
  if (!customerId.value) return
  aiStale.value = false
  status.value = '画像生成中…'
  const prevDraftId = profile.value?.draft?.id ?? null
  await api('/sidebar/profile/generate', {
    method: 'POST',
    body: JSON.stringify({ customer_id: customerId.value, force: true }),
  })
  for (let i = 0; i < 40; i++) {
    profile.value = await api(`/sidebar/profile?customer_id=${customerId.value}`)
    const nextId = profile.value?.draft?.id
    // 等新草稿 id，或生成结束且草稿已更新
    if (nextId != null && nextId !== prevDraftId) break
    if (!profile.value?.generating && nextId != null && nextId !== prevDraftId) break
    await new Promise((r) => setTimeout(r, 800))
  }
  const fresh =
    profile.value?.draft?.id != null && profile.value.draft.id !== prevDraftId
  notify(fresh ? '画像草稿已更新' : '画像生成中，请稍后查看', fresh ? 'ok' : 'info')
}

async function confirm(mode: 'all' | 'discard') {
  if (!profile.value?.draft) return
  const hadConfirmed = Boolean(
    profile.value?.confirmed &&
      ['basic_info', 'study_info', 'prefer_info', 'timeline'].some((k) => {
        const v = profile.value.confirmed[k]
        if (v == null) return false
        if (Array.isArray(v)) return v.length > 0
        if (typeof v === 'object') return Object.keys(v).length > 0
        return true
      }),
  )
  try {
    await api('/sidebar/profile/confirm', {
      method: 'POST',
      body: JSON.stringify({
        draft_id: profile.value.draft.id,
        mode,
        fields: [],
      }),
    })
    await refreshAll()
    if (mode === 'discard') {
      notify(
        hadConfirmed
          ? '已丢弃剩余草稿；已生效画像已保留'
          : '已丢弃草稿；正式画像未变更',
        'warn',
      )
    } else {
      notify('已全部确认并写入正式画像', 'ok')
    }
  } catch (e: any) {
    notify(String(e?.message || e || '操作失败'), 'err')
  }
}

async function confirmField(field: string) {
  if (!profile.value?.draft) return
  const titles: Record<string, string> = {
    basic_info: '基本信息',
    study_info: '学情',
    prefer_info: '偏好',
    timeline: '时间线',
  }
  try {
    const data = await api('/sidebar/profile/confirm', {
      method: 'POST',
      body: JSON.stringify({
        draft_id: profile.value.draft.id,
        mode: 'fields',
        fields: [field],
      }),
    })
    await refreshAll()
    if (data?.draft_status === 'merged') {
      notify('四个分区均已确认并生效，草稿已合并', 'ok')
    } else {
      notify(`「${titles[field] || field}」已写入正式画像，其余分区仍待确认`, 'ok')
    }
  } catch (e: any) {
    notify(String(e?.message || e || '确认分区失败'), 'err')
  }
}

async function patchField(field: string, value: unknown) {
  if (!profile.value?.draft) return
  try {
    await api('/sidebar/profile/draft', {
      method: 'PATCH',
      body: JSON.stringify({
        draft_id: profile.value.draft.id,
        field,
        value,
      }),
    })
    await refreshAll()
    notify('已保存草稿修改', 'ok')
  } catch (e: any) {
    notify(String(e?.message || e || '保存草稿失败'), 'err')
  }
}

async function suggestSchedule() {
  if (!customerId.value) return
  aiStale.value = false
  tab.value = 'schedule'
  await schedulePanel.value?.suggest()
}

function openWeakTipSchedule() {
  tab.value = 'schedule'
  weakTip.value = null
  notify('已打开日程', 'info')
  void schedulePanel.value?.load()
}

function onPanelStatus(msg: string) {
  const lower = msg.toLowerCase()
  const kind =
    /失败|错误|不可|拒绝/.test(msg) || lower.includes('fail')
      ? 'err'
      : /降级|跳过|不适用|忽略|丢弃/.test(msg)
        ? 'warn'
        : /已|成功|就绪|复制/.test(msg)
          ? 'ok'
          : 'info'
  notify(msg, kind)
}

function handleLogout() {
  sse.disconnect()
  logout()
  ready.value = false
  customerId.value = null
  context.value = null
  profile.value = null
  tags.value = null
  reply.value = null
  customers.value = []
  aiStale.value = false
}

async function initAuth() {
  const result = await bootSession()
  if (result === 'login') {
    ready.value = false
    return
  }
  if (result === 'redirect') return
  ready.value = true
  await enterWorkbench()
}

onMounted(() => {
  void loadHealth()
  void initAuth()
})

onUnmounted(() => {
  sse.disconnect()
})
</script>

<template>
  <LoginView v-if="!loggedIn" @logged-in="onLoggedIn" />

  <div
    v-else-if="!ready"
    class="flex min-h-screen items-center justify-center bg-stone-50 text-sm text-muted"
  >
    加载中…
  </div>

  <main v-else class="mx-auto max-w-[1180px] px-4 pb-7 pt-3">
    <CapabilityBar :flags="healthFlags" />
    <AppToast />

    <header
      class="sticky top-0 z-20 mb-1 border-b border-line bg-stone-50/90 py-2 backdrop-blur-sm max-md:static max-md:backdrop-blur-none"
    >
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p class="m-0 font-display text-[13px] font-bold tracking-wide text-fjord">擎天学智</p>
          <h1 class="mt-0.5 font-display text-xl font-semibold text-ink">顾问工作台</h1>
          <p class="mt-1 text-xs text-muted">{{ status || authStatus }}</p>
          <p v-if="me" class="mt-0.5 text-xs text-muted">{{ me.name }} · 顾问</p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button
            type="button"
            class="whitespace-nowrap rounded-control border border-line bg-white px-3 py-1.5 text-sm text-muted hover:bg-stone-50"
            @click="showChat = !showChat"
          >
            {{ showChat ? '隐藏会话' : '会话' }}
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-1.5 rounded-control border border-line bg-white px-3 py-1.5 text-sm text-muted hover:bg-stone-50"
            @click="handleLogout"
          >
            <UiIcon :icon="LogOut" :size="16" />
            退出
          </button>
        </div>
      </div>
    </header>

    <details
      class="mb-2.5 rounded-panel border border-dashed border-line bg-stone-50 px-2.5 py-1 opacity-90"
      :open="demoOpen"
      @toggle="demoOpen = ($event.target as HTMLDetailsElement).open"
    >
      <summary class="cursor-pointer select-none text-[11px] text-muted">演示模式</summary>
      <div class="flex flex-wrap items-center gap-2 py-2">
        <button
          type="button"
          class="rounded-control border border-line bg-white px-2 py-1 text-xs hover:bg-stone-50"
          @click="seedPhysicsScenario"
        >
          物理场景
        </button>
        <button
          type="button"
          class="rounded-control border border-line bg-white px-2 py-1 text-xs hover:bg-stone-50"
          @click="mockExchange"
        >
          Mock 企微换票
        </button>
        <span class="text-xs text-muted">SSE：{{ sseLog || '等待连接…' }}</span>
      </div>
    </details>

    <WeakTipBar
      v-if="weakTip"
      :text="weakTip.text"
      :priority="weakTip.priority"
      @dismiss="weakTip = null"
      @open="openWeakTipSchedule"
    />

    <div
      class="mt-2.5 grid items-stretch gap-3.5 max-md:grid-cols-1"
      :class="showChat ? 'md:grid-cols-[minmax(0,1.1fr)_minmax(300px,0.9fr)]' : 'grid-cols-1'"
    >
      <aside v-show="showChat" class="min-h-[520px] max-md:order-2 max-md:min-h-[360px]">
        <ChatPanel
          ref="chatPanel"
          :api="api"
          :customer-id="customerId"
          :customers="customers"
          @status="onPanelStatus"
          @refreshed="refreshAll"
          @stale="onChatStale"
          @select-customer="onSelectCustomer"
          @goto-tab="(t) => (tab = t)"
          @use-reply="suggestReply"
          @use-schedule="suggestSchedule"
        />
      </aside>

      <section class="min-w-0 max-md:order-1">
        <CustomerHeader :context="context" :customer-id="customerId" />

        <nav
          class="mb-2.5 flex gap-0.5 rounded-panel bg-stone-100 p-0.5"
          role="tablist"
        >
          <button
            v-for="t in tabs"
            :key="t.id"
            type="button"
            role="tab"
            class="relative flex flex-1 items-center justify-center gap-1.5 rounded-control px-1.5 py-2 text-sm font-medium transition-colors"
            :class="
              tab === t.id
                ? 'bg-white font-bold text-fjord shadow-soft'
                : 'bg-transparent text-muted hover:text-ink'
            "
            :aria-selected="tab === t.id"
            @click="tab = t.id"
          >
            <UiIcon :icon="t.icon" :size="16" />
            {{ t.label }}
            <span
              v-if="aiStale"
              class="absolute -right-0.5 -top-0.5 rounded-full bg-signal px-1 py-px text-[9px] font-semibold leading-none text-white"
            >
              可更新
            </span>
          </button>
        </nav>

        <Transition
          enter-active-class="transition-opacity duration-150"
          leave-active-class="transition-opacity duration-150"
          enter-from-class="opacity-0"
          leave-to-class="opacity-0"
          mode="out-in"
        >
          <div
            v-if="tab !== 'schedule'"
            :key="tab"
            class="min-h-[420px] rounded-panel border border-line border-l-[3px] border-l-fjord bg-white p-3.5 shadow-soft"
          >
            <ProfilePanel
              v-if="tab === 'profile'"
              :profile="profile"
              :generating="generating"
              @generate="generate"
              @confirm="confirm"
              @confirm-field="confirmField"
              @patch-field="patchField"
            />
            <TagsPanel
              v-else-if="tab === 'tags'"
              :api="api"
              :customer-id="customerId"
              :tags="tags"
              :recommend-busy="tagRecommendBusy"
              @recommend="recommendTags"
              @status="onPanelStatus"
              @refreshed="refreshTags"
            />
            <SuggestPanel
              v-else-if="tab === 'suggest'"
              :reply="reply"
              :reply-scene="replyScene"
              :reply-busy="replyBusy"
              :last-asr="lastAsr"
              :outcome="replyOutcome"
              @update:reply-scene="onSceneChange"
              @suggest="suggestReply"
              @feedback="replyFeedback"
              @clear-outcome="clearReplyOutcome"
              @status="onPanelStatus"
            />
          </div>
        </Transition>
        <div
          v-show="tab === 'schedule'"
          class="min-h-[420px] rounded-panel border border-line border-l-[3px] border-l-fjord bg-white p-3.5 shadow-soft"
        >
          <SchedulePanel
            ref="schedulePanel"
            :api="api"
            :customer-id="customerId"
            @status="onPanelStatus"
            @suggest-started="aiStale = false"
          />
        </div>
      </section>
    </div>
  </main>
</template>
