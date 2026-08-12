<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import SchedulePanel from './components/SchedulePanel.vue'
import WeakTipBar from './components/WeakTipBar.vue'
import { createApi } from './composables/useApi'
import { createSseClient } from './composables/useSse'

const status = ref('idle')
const token = ref('')
const customerId = ref<number | null>(null)
const externalUserId = ref('demo_wang')
const tab = ref<'profile' | 'tags' | 'suggest' | 'schedule'>('profile')
const context = ref<any>(null)
const profile = ref<any>(null)
const tags = ref<any>(null)
const reply = ref<any>(null)
const replyScene = ref<'sales' | 'cs'>('sales')
const replyBusy = ref(false)
const asrBusy = ref(false)
const asrHint = ref('下周周六上午方便来试听吗')
const lastAsr = ref<string | null>(null)
const customers = ref<any[]>([])
const mockReply = ref('')
const mockDirection = ref<'in' | 'out'>('in')
const sseLog = ref('')
const weakTip = ref<{ text: string; priority?: string } | null>(null)
const schedulePanel = ref<{ load: () => Promise<void> } | null>(null)

const api = createApi(() => token.value)
const draft = computed(() => profile.value?.draft)
const confirmed = computed(() => profile.value?.confirmed)
const generating = computed(() => !!profile.value?.generating)
const recommendations = computed(() => tags.value?.recommendations)

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
  status.value = `已切换客户 #${customerId.value}`
  await refreshAll()
  sse.connect()
}

async function refreshAll() {
  if (!customerId.value) return
  const q = `customer_id=${customerId.value}`
  context.value = await api(`/sidebar/context?${q}`)
  profile.value = await api(`/sidebar/profile?${q}`)
  tags.value = await api(`/sidebar/tags?${q}`)
  reply.value = await api(`/sidebar/reply/latest?${q}&scene=${replyScene.value}`)
  if (tab.value === 'schedule') await schedulePanel.value?.load()
}

async function suggestReply() {
  if (!customerId.value) return
  replyBusy.value = true
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
    reply.value = await api(
      `/sidebar/reply/latest?customer_id=${customerId.value}&scene=${replyScene.value}`,
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
  if (action === 'copy' && reply.value.primary) {
    try {
      await navigator.clipboard.writeText(reply.value.primary)
    } catch {
      /* clipboard may be blocked */
    }
  }
  await api('/sidebar/reply/feedback', {
    method: 'POST',
    body: JSON.stringify({
      suggestion_id: reply.value.suggestion_id,
      action,
      edited_content: action === 'edit_adopt' ? text || reply.value.primary : undefined,
    }),
  })
  status.value =
    action === 'copy'
      ? '已复制（请到企微手动发送，系统不代发）'
      : action === 'reject'
        ? '已标记不适用'
        : '已记录采纳'
  reply.value = await api(
    `/sidebar/reply/latest?customer_id=${customerId.value}&scene=${replyScene.value}`,
  )
}

async function transcribeVoice() {
  if (!customerId.value) return
  asrBusy.value = true
  status.value = '语音转写中…'
  try {
    const data = await api('/sidebar/asr/transcribe', {
      method: 'POST',
      body: JSON.stringify({
        customer_id: customerId.value,
        audio_ref: `mock://voice/${Date.now()}.wav`,
        content_hint: asrHint.value || undefined,
        create_message: true,
      }),
    })
    lastAsr.value = data.asr_text || null
    status.value = lastAsr.value ? `已转写：${lastAsr.value}` : '转写完成'
    await refreshAll()
  } catch (e: any) {
    lastAsr.value = null
    status.value = e?.message || '转写失败，不阻断文本建议'
  } finally {
    asrBusy.value = false
  }
}

async function recommendTags() {
  if (!customerId.value) return
  status.value = '生成标签推荐…'
  await api('/sidebar/tags/recommend', {
    method: 'POST',
    body: JSON.stringify({ customer_id: customerId.value, force: true }),
  })
  tags.value = await api(`/sidebar/tags?customer_id=${customerId.value}`)
}

async function confirmTagRecommend(apply: boolean) {
  const rec = recommendations.value
  if (!rec?.suggestion_id) return
  await api('/sidebar/tags/recommend/confirm', {
    method: 'POST',
    body: JSON.stringify({
      suggestion_id: rec.suggestion_id,
      apply_add: apply,
      apply_remove: apply,
    }),
  })
  status.value = apply ? '已确认标签推荐' : '已忽略标签推荐'
  await refreshAll()
}

async function sendMockReply() {
  if (!customerId.value || !mockReply.value.trim()) return
  await api('/mock/messages', {
    method: 'POST',
    body: JSON.stringify({
      customer_id: customerId.value,
      direction: mockDirection.value,
      content: mockReply.value.trim(),
    }),
  })
  mockReply.value = ''
  status.value = '已写入模拟回复'
  await refreshAll()
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
  sse.connect()
}

async function generate() {
  if (!customerId.value) return
  status.value = '画像生成中…'
  await api('/sidebar/profile/generate', {
    method: 'POST',
    body: JSON.stringify({ customer_id: customerId.value, force: true }),
  })
  profile.value = await api(`/sidebar/profile?customer_id=${customerId.value}`)
}

async function confirm(mode: 'all' | 'discard', fields?: string[]) {
  if (!draft.value) return
  await api('/sidebar/profile/confirm', {
    method: 'POST',
    body: JSON.stringify({
      draft_id: draft.value.id,
      mode,
      fields: fields || [],
    }),
  })
  await refreshAll()
  status.value = mode === 'discard' ? '已忽略草稿' : '已确认画像'
}

async function confirmField(field: string) {
  if (!draft.value) return
  await api('/sidebar/profile/confirm', {
    method: 'POST',
    body: JSON.stringify({
      draft_id: draft.value.id,
      mode: 'fields',
      fields: [field],
    }),
  })
  await refreshAll()
}

async function removeTag(customerTagId: number) {
  await api(`/sidebar/tags/${customerTagId}`, { method: 'DELETE' })
  await refreshAll()
}

onMounted(() => {
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
    <header class="head">
      <div>
        <h1>擎天学智 · 侧边栏</h1>
        <p class="sub">{{ status }}</p>
      </div>
      <button type="button" @click="exchange">重新换票</button>
    </header>

    <WeakTipBar
      v-if="weakTip"
      :text="weakTip.text"
      :priority="weakTip.priority"
      @dismiss="weakTip = null"
    />

    <section class="card mock-panel">
      <div class="title-row">
        <h2>Mock 演示</h2>
        <button type="button" @click="seedPhysicsScenario">一键物理场景</button>
      </div>
      <div class="title-row">
        <label>
          external_userid
          <input v-model="externalUserId" placeholder="demo_wang" />
        </label>
        <label>
          客户
          <select v-model.number="customerId" @change="switchCustomer">
            <option v-for="c in customers" :key="c.id" :value="c.id">
              #{{ c.id }} {{ c.parent_name }}/{{ c.student_name || '—' }}
              ({{ c.external_id || 'no-ext' }})
            </option>
          </select>
        </label>
      </div>
      <div class="title-row">
        <select v-model="mockDirection">
          <option value="in">客户回复 (in)</option>
          <option value="out">顾问发送 (out)</option>
        </select>
        <input
          v-model="mockReply"
          class="grow"
          placeholder="模拟一条聊天内容后生成画像"
          @keyup.enter="sendMockReply"
        />
        <button type="button" @click="sendMockReply">写入回复</button>
      </div>
      <div class="title-row">
        <input
          v-model="asrHint"
          class="grow"
          placeholder="语音 content_hint（Fake ASR）"
        />
        <button type="button" :disabled="asrBusy" @click="transcribeVoice">
          {{ asrBusy ? '转写中…' : '模拟语音转写' }}
        </button>
      </div>
      <p v-if="lastAsr" class="muted">最近转写：{{ lastAsr }}</p>
      <p class="muted">
        流程：切客户 / 写入回复 / 转写 → 生成画像 / 话术 / 日程。
      </p>
    </section>

    <section v-if="context" class="card">
      <div class="title-row">
        <strong>{{ context.customer.parent_name }} / {{ context.customer.student_name }}</strong>
        <span>{{ context.customer.grade }} · {{ context.customer.school }}</span>
      </div>
      <div class="tags">
        <span v-for="t in context.tags" :key="t.id" class="chip">{{ t.name }}</span>
      </div>
      <p class="muted">顾问：{{ context.customer.owner_name || '—' }} · customer_id={{ customerId }}</p>
    </section>

    <nav class="tabs">
      <button :class="{ active: tab === 'profile' }" type="button" @click="tab = 'profile'">画像</button>
      <button :class="{ active: tab === 'tags' }" type="button" @click="tab = 'tags'">标签</button>
      <button :class="{ active: tab === 'suggest' }" type="button" @click="tab = 'suggest'">建议</button>
      <button :class="{ active: tab === 'schedule' }" type="button" @click="tab = 'schedule'">日程</button>
    </nav>

    <section v-if="tab === 'profile'" class="card">
      <div class="title-row">
        <h2>客户画像 <em class="ai">AI 建议</em></h2>
        <button type="button" :disabled="generating" @click="generate">
          {{ generating ? '生成中…' : '生成画像' }}
        </button>
      </div>

      <div v-if="draft" class="draft">
        <p class="muted">
          置信度 {{ draft.confidence ?? '—' }} ·
          来源 {{ (draft.sources || []).map((s: any) => s.label || s.type).join(' / ') || '—' }}
        </p>
        <div v-for="field in ['basic_info', 'study_info', 'prefer_info', 'timeline']" :key="field" class="block">
          <div class="title-row">
            <strong>{{ field }}</strong>
            <button type="button" @click="confirmField(field)">确认本区</button>
          </div>
          <pre>{{ JSON.stringify(draft[field], null, 2) }}</pre>
        </div>
        <div class="actions">
          <button type="button" class="primary" @click="confirm('all')">全部确认</button>
          <button type="button" @click="confirm('discard')">忽略草稿</button>
        </div>
      </div>
      <p v-else class="muted">暂无草稿。可点击「生成画像」。</p>

      <h3>已确认</h3>
      <pre v-if="confirmed">{{ JSON.stringify(confirmed, null, 2) }}</pre>
      <p v-else class="muted">尚无已确认画像</p>
      <p class="muted">SSE：{{ sseLog || '等待连接…' }}</p>
    </section>

    <section v-else-if="tab === 'tags'" class="card">
      <div class="title-row">
        <h2>标签 <em class="ai">AI 建议</em></h2>
        <button type="button" @click="recommendTags">生成推荐</button>
      </div>
      <ul class="list">
        <li v-for="t in tags?.active || []" :key="t.customer_tag_id">
          <div>
            <strong>{{ t.name }}</strong>
            <p class="muted">{{ t.sop_text || '无 SOP' }}</p>
          </div>
          <button type="button" @click="removeTag(t.customer_tag_id)">移除</button>
        </li>
      </ul>

      <div v-if="recommendations" class="block">
        <h3>推荐草稿 #{{ recommendations.suggestion_id }}</h3>
        <p class="muted">确认前不会写入正式标签</p>
        <div v-for="(a, i) in recommendations.add || []" :key="'a'+i" class="chip-row">
          <span class="chip">+ {{ a.tag_name || a.name }}</span>
          <span class="muted">{{ a.reason }}</span>
        </div>
        <div v-for="(a, i) in recommendations.remove || []" :key="'r'+i" class="chip-row">
          <span class="chip danger">- {{ a.tag_name || a.name }}</span>
          <span class="muted">{{ a.reason }}</span>
        </div>
        <div class="actions">
          <button type="button" class="primary" @click="confirmTagRecommend(true)">确认推荐</button>
          <button type="button" @click="confirmTagRecommend(false)">忽略</button>
        </div>
      </div>
      <p v-else class="muted">暂无 AI 标签推荐。可点「生成推荐」。</p>
    </section>

    <section v-else-if="tab === 'suggest'" class="card">
      <div class="title-row">
        <h2>回复建议 <em class="ai">AI 建议</em></h2>
        <select v-model="replyScene" @change="refreshAll">
          <option value="sales">销售</option>
          <option value="cs">客服</option>
        </select>
        <button type="button" :disabled="replyBusy" @click="suggestReply">
          {{ replyBusy ? '生成中…' : '生成建议' }}
        </button>
      </div>
      <p class="muted">不会自动发送；请复制后到企微手动发送。</p>
      <p v-if="reply?.based_on_asr || lastAsr" class="asr-banner">
        基于转写：{{ reply?.based_on_asr || lastAsr }}
      </p>

      <div v-if="reply?.primary">
        <h3>主建议</h3>
        <pre>{{ reply.primary }}</pre>
        <div class="actions">
          <button type="button" class="primary" @click="replyFeedback('copy')">复制</button>
          <button type="button" @click="replyFeedback('adopt')">采纳</button>
          <button type="button" @click="replyFeedback('edit_adopt', reply.primary)">编辑后采纳</button>
          <button type="button" @click="replyFeedback('reject')">不适用</button>
        </div>
        <div v-if="(reply.alternatives || []).length" class="block">
          <h3>备选</h3>
          <pre v-for="(alt, i) in reply.alternatives" :key="i">{{ alt }}</pre>
        </div>
      </div>
      <p v-else class="muted">暂无建议。可点击「生成建议」。</p>
      <p class="muted">SSE：{{ sseLog || '等待连接…' }}</p>
    </section>

    <SchedulePanel
      v-show="tab === 'schedule'"
      ref="schedulePanel"
      :api="api"
      :customer-id="customerId"
      @status="(msg) => (status = msg)"
    />
  </main>
</template>

<style scoped>
.page {
  max-width: 720px;
  margin: 0 auto;
  padding: 16px;
  font-family: "Segoe UI", "PingFang SC", sans-serif;
  color: #1f2a37;
}
.head, .title-row, .actions, .tabs {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.head { justify-content: space-between; margin-bottom: 12px; }
h1 { margin: 0; font-size: 1.25rem; }
h2 { margin: 0; font-size: 1.05rem; }
.sub, .muted { color: #667085; margin: 4px 0; }
.card {
  background: rgba(255,255,255,0.9);
  border: 1px solid #e4e7ec;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 12px;
}
.mock-panel input, .mock-panel select {
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  padding: 6px 8px;
  font: inherit;
}
.mock-panel .grow { flex: 1; min-width: 180px; }
.chip {
  display: inline-block;
  background: #eef4ff;
  color: #3538cd;
  border-radius: 999px;
  padding: 2px 10px;
  margin: 2px 4px 2px 0;
  font-size: 12px;
}
.chip.danger { background: #fef3f2; color: #b42318; }
.chip-row { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; margin: 4px 0; }
.tabs button {
  border: 1px solid #d0d5dd;
  background: #fff;
  border-radius: 8px;
  padding: 6px 10px;
}
.tabs button.active { background: #1f2a37; color: #fff; }
button {
  border: 1px solid #d0d5dd;
  background: #fff;
  border-radius: 8px;
  padding: 6px 10px;
  cursor: pointer;
}
button.primary { background: #175cd3; color: #fff; border-color: #175cd3; }
button:disabled { opacity: 0.5; cursor: not-allowed; }
.ai { color: #6941c6; font-style: normal; font-size: 12px; margin-left: 6px; }
.asr-banner {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  padding: 8px 10px;
  color: #075985;
  margin: 8px 0;
  font-size: 13px;
}
pre {
  background: #f8fafc;
  border: 1px solid #e4e7ec;
  border-radius: 8px;
  padding: 8px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}
.block { margin: 10px 0; }
.list { list-style: none; padding: 0; margin: 0; }
.list li {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #eef2f6;
}
</style>
