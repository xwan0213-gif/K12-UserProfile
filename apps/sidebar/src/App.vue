<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import CapabilityBar from './components/CapabilityBar.vue'
import CustomerHeader from './components/CustomerHeader.vue'
import ChatPanel from './components/chat/ChatPanel.vue'
import ProfilePanel from './components/profile/ProfilePanel.vue'
import SuggestPanel from './components/suggest/SuggestPanel.vue'
import type { ReplyOutcome } from './components/suggest/SuggestPanel.vue'
import TagsPanel from './components/tags/TagsPanel.vue'
import SchedulePanel from './components/SchedulePanel.vue'
import WeakTipBar from './components/WeakTipBar.vue'
import { createApi } from './composables/useApi'
import { createSseClient } from './composables/useSse'

const status = ref('idle')
const token = ref('')
const customerId = ref<number | null>(null)
const externalUserId = ref('demo_wang')
const tab = ref<'profile' | 'tags' | 'suggest' | 'schedule'>('profile')
const showChat = ref(true)
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
})

const api = createApi(() => token.value)
const generating = computed(() => !!profile.value?.generating)

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
        status.value = '收到弱提醒'
      } catch {
        weakTip.value = { text: data || '日程提醒' }
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
      status.value =
        ev === 'profile_draft'
          ? '收到画像草稿'
          : ev === 'reply_ready'
            ? '收到话术建议'
            : ev === 'tag_recommend'
              ? '收到标签推荐'
              : ev === 'schedule_draft'
                ? '收到日程草稿'
                : '生成失败'
    }
  },
})

async function loadHealth() {
  try {
    const res = await fetch('/health')
    const json = await res.json()
    const d = json?.data || json
    healthFlags.value = {
      mockWecom: !!d.mock_wecom,
      mockLlm: !!d.mock_llm,
      llmProvider: d.llm_provider || 'deepseek',
      asr: d.mock_llm ? 'Fake' : 'Fake/Stub',
      calendar: '降级',
    }
  } catch {
    /* ignore */
  }
}

async function loadCustomers() {
  const data = await api('/mock/customers')
  customers.value = data.items || []
}

async function exchange() {
  status.value = '换票中…'
  const data = await api('/auth/wecom/exchange', {
    method: 'POST',
    body: JSON.stringify({
      code: 'mock_code',
      external_userid: externalUserId.value || undefined,
    }),
  })
  token.value = data.access_token
  if (data.customer_id) customerId.value = data.customer_id
  status.value = `已登录：${data.user.name}`
  await loadCustomers()
  if (!customerId.value && customers.value.length) {
    customerId.value = customers.value[0].id
  }
  await refreshAll()
  sse.connect()
}

async function switchCustomer() {
  if (!customerId.value) return
  const selected = customers.value.find((c) => c.id === customerId.value)
  if (selected?.external_id) externalUserId.value = selected.external_id
  replyOutcome.value = null
  status.value = `已切换客户 #${customerId.value}`
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

async function onSceneChange(scene: 'sales' | 'cs') {
  replyScene.value = scene
  replyOutcome.value = null
  await refreshAll()
}

async function suggestReply() {
  if (!customerId.value) return
  replyBusy.value = true
  replyOutcome.value = null
  status.value = '生成话术建议…'
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
      if (reply.value?.primary) break
      await new Promise((r) => setTimeout(r, 800))
    }
    if (reply.value?.based_on_asr) lastAsr.value = reply.value.based_on_asr
    status.value = reply.value?.primary ? '已生成话术建议' : '话术生成中，请稍后查看'
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
    status.value = '已复制（请到企微手动发送，系统不代发）'
    // copy 后 status 仍为 shown，保留当前建议
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
  status.value =
    action === 'reject'
      ? '已标记不适用（不会代发）'
      : action === 'edit_adopt'
        ? '已按编辑稿标记有用（不会代发）'
        : '已标记有用（不会代发）'

  reply.value = await api(
    `/sidebar/reply/latest?customer_id=${customerId.value}&scene=${replyScene.value}`,
  )
}

function clearReplyOutcome() {
  replyOutcome.value = null
}

async function recommendTags() {
  if (!customerId.value || tagRecommendBusy.value) return
  tagRecommendBusy.value = true
  status.value = '生成标签推荐…'
  try {
    await api('/sidebar/tags/recommend', {
      method: 'POST',
      body: JSON.stringify({ customer_id: customerId.value, force: true }),
    })
    for (let i = 0; i < 40; i++) {
      tags.value = await api(`/sidebar/tags?customer_id=${customerId.value}`)
      if (tags.value?.recommendations) break
      await new Promise((r) => setTimeout(r, 800))
    }
    status.value = tags.value?.recommendations
      ? '已收到标签推荐'
      : '标签推荐生成中，请稍后刷新'
  } catch (e: any) {
    status.value = e?.message || '标签推荐失败'
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
  status.value = `场景就绪：客户 #${data.customer_id}`
  await refreshAll()
  await chatPanel.value?.load()
  sse.connect()
}

async function generate() {
  if (!customerId.value) return
  status.value = '画像生成中…'
  await api('/sidebar/profile/generate', {
    method: 'POST',
    body: JSON.stringify({ customer_id: customerId.value, force: true }),
  })
  for (let i = 0; i < 40; i++) {
    profile.value = await api(`/sidebar/profile?customer_id=${customerId.value}`)
    if (profile.value?.draft) break
    await new Promise((r) => setTimeout(r, 800))
  }
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
      status.value = hadConfirmed
        ? '已丢弃剩余草稿；已生效画像已保留'
        : '已丢弃草稿；正式画像未变更'
    } else {
      status.value = '已全部确认并写入正式画像'
    }
  } catch (e: any) {
    status.value = String(e?.message || e || '操作失败')
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
      status.value = '四个分区均已确认并生效，草稿已合并'
    } else {
      status.value = `「${titles[field] || field}」已写入正式画像，其余分区仍待确认`
    }
  } catch (e: any) {
    status.value = String(e?.message || e || '确认分区失败')
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
    status.value = '已保存草稿修改'
  } catch (e: any) {
    status.value = String(e?.message || e || '保存草稿失败')
  }
}

async function suggestSchedule() {
  if (!customerId.value) return
  tab.value = 'schedule'
  await schedulePanel.value?.suggest()
}

onMounted(() => {
  void loadHealth()
  void exchange().catch((e) => {
    status.value = String(e.message || e)
  })
})

onUnmounted(() => {
  sse.disconnect()
})
</script>

<template>
  <main class="page">
    <CapabilityBar :flags="healthFlags" />

    <header class="top">
      <div>
        <h1>侧边栏工作台</h1>
        <p class="sub">{{ status }}</p>
      </div>
      <div class="top-actions">
        <button type="button" class="chat-toggle" @click="showChat = !showChat">
          {{ showChat ? '隐藏会话' : '会话' }}
        </button>
        <button type="button" @click="seedPhysicsScenario">物理场景</button>
        <button type="button" @click="exchange">重新换票</button>
      </div>
    </header>

    <div class="toolbar">
      <label>
        客户
        <select v-model.number="customerId" @change="switchCustomer">
          <option v-for="c in customers" :key="c.id" :value="c.id">
            #{{ c.id }} {{ c.parent_name }}/{{ c.student_name || '—' }}
          </option>
        </select>
      </label>
      <span class="muted">SSE：{{ sseLog || '等待连接…' }}</span>
    </div>

    <WeakTipBar
      v-if="weakTip"
      :text="weakTip.text"
      :priority="weakTip.priority"
      @dismiss="weakTip = null"
    />

    <div class="bench" :class="{ 'chat-hidden': !showChat }">
      <aside v-show="showChat" class="chat-col">
        <ChatPanel
          ref="chatPanel"
          :api="api"
          :customer-id="customerId"
          @status="(msg) => (status = msg)"
          @refreshed="refreshAll"
          @goto-tab="(t) => (tab = t)"
          @use-reply="suggestReply"
          @use-schedule="suggestSchedule"
        />
      </aside>

      <section class="side-col">
        <CustomerHeader :context="context" :customer-id="customerId" />

        <nav class="tabs">
          <button :class="{ active: tab === 'profile' }" type="button" @click="tab = 'profile'">画像</button>
          <button :class="{ active: tab === 'tags' }" type="button" @click="tab = 'tags'">标签</button>
          <button :class="{ active: tab === 'suggest' }" type="button" @click="tab = 'suggest'">建议</button>
          <button :class="{ active: tab === 'schedule' }" type="button" @click="tab = 'schedule'">日程</button>
        </nav>

        <div class="side-body card">
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
            @status="(msg) => (status = msg)"
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
            @status="(msg) => (status = msg)"
          />
          <SchedulePanel
            v-show="tab === 'schedule'"
            ref="schedulePanel"
            :api="api"
            :customer-id="customerId"
            @status="(msg) => (status = msg)"
          />
        </div>
      </section>
    </div>
  </main>
</template>

<style scoped>
.page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 14px 16px 24px;
}
.top, .top-actions, .toolbar, .tabs {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.top { justify-content: space-between; margin-bottom: 8px; }
h1 {
  margin: 0;
  font-size: 1.2rem;
  font-family: var(--font-display);
}
.sub { color: var(--muted); margin: 4px 0 0; font-size: 13px; }
.toolbar {
  margin-bottom: 10px;
  justify-content: space-between;
}
.toolbar select {
  margin-left: 6px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 8px;
}
.bench {
  display: grid;
  grid-template-columns: minmax(280px, 1.1fr) minmax(300px, 0.9fr);
  gap: 12px;
  align-items: stretch;
}
.bench.chat-hidden {
  grid-template-columns: 1fr;
}
.chat-col { min-height: 520px; }
.side-col { min-width: 0; }
.card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 12px;
  box-shadow: var(--shadow);
}
.tabs { margin-bottom: 8px; }
.tabs button.active {
  background: var(--ink);
  color: #fff;
  border-color: var(--ink);
}
.side-body { min-height: 420px; }
.chat-toggle {
  background: var(--accent-soft);
  border-color: var(--accent);
  color: var(--accent);
}

@media (max-width: 900px) {
  .bench {
    grid-template-columns: 1fr;
  }
  .chat-col {
    order: 2;
    min-height: 360px;
  }
  .side-col { order: 1; }
}
</style>
