<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

const apiBase = '/api/v1'
const status = ref('idle')
const token = ref('')
const customerId = ref<number | null>(null)
const tab = ref<'profile' | 'tags' | 'suggest' | 'schedule'>('profile')
const context = ref<any>(null)
const profile = ref<any>(null)
const tags = ref<any>(null)
const sseLog = ref('')
let sseAbort: AbortController | null = null
let reconnectTimer: number | null = null

const draft = computed(() => profile.value?.draft)
const confirmed = computed(() => profile.value?.confirmed)
const generating = computed(() => !!profile.value?.generating)

async function api(path: string, init: RequestInit = {}) {
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string> | undefined),
  }
  if (token.value) headers.Authorization = `Bearer ${token.value}`
  if (init.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json'
  const res = await fetch(`${apiBase}${path}`, { ...init, headers })
  const json = await res.json()
  if (json.code !== 0) throw new Error(json.message || '请求失败')
  return json.data
}

async function exchange() {
  status.value = '换票中…'
  const data = await api('/auth/wecom/exchange', {
    method: 'POST',
    body: JSON.stringify({ code: 'mock_code', external_userid: 'demo_wang' }),
  })
  token.value = data.access_token
  customerId.value = data.customer_id
  status.value = `已登录：${data.user.name}`
  await refreshAll()
  connectSse()
}

async function refreshAll() {
  if (!customerId.value) return
  const q = `customer_id=${customerId.value}`
  context.value = await api(`/sidebar/context?${q}`)
  profile.value = await api(`/sidebar/profile?${q}`)
  tags.value = await api(`/sidebar/tags?${q}`)
  // reuse admin tags list via mock-friendly public isn't available; skip catalog for add
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

function connectSse() {
  if (!token.value || !customerId.value) return
  sseAbort?.abort()
  const ctrl = new AbortController()
  sseAbort = ctrl
  void (async () => {
    try {
      const res = await fetch(
        `${apiBase}/sidebar/sse?customer_id=${customerId.value}`,
        {
          headers: {
            Authorization: `Bearer ${token.value}`,
            Accept: 'text/event-stream',
          },
          signal: ctrl.signal,
        },
      )
      if (!res.body) return
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const parts = buf.split('\n\n')
        buf = parts.pop() || ''
        for (const part of parts) {
          const ev = /event:\s*(\w+)/.exec(part)?.[1]
          const dataLine = part.split('\n').find((l) => l.startsWith('data:'))
          const data = dataLine ? dataLine.slice(5).trim() : ''
          sseLog.value = `${ev}: ${data}`
          if (ev === 'profile_draft' || ev === 'job_failed') {
            await refreshAll()
            status.value = ev === 'profile_draft' ? '收到画像草稿' : '生成失败'
          }
        }
      }
    } catch (e: any) {
      if (e?.name === 'AbortError') return
      status.value = 'SSE 断开，重连中…'
      reconnectTimer = window.setTimeout(connectSse, 2000)
    }
  })()
}

onMounted(() => {
  void exchange().catch((e) => {
    status.value = String(e.message || e)
  })
})

onUnmounted(() => {
  sseAbort?.abort()
  if (reconnectTimer) window.clearTimeout(reconnectTimer)
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

    <section v-if="context" class="card">
      <div class="title-row">
        <strong>{{ context.customer.parent_name }} / {{ context.customer.student_name }}</strong>
        <span>{{ context.customer.grade }} · {{ context.customer.school }}</span>
      </div>
      <div class="tags">
        <span v-for="t in context.tags" :key="t.id" class="chip">{{ t.name }}</span>
      </div>
      <p class="muted">顾问：{{ context.customer.owner_name || '—' }}</p>
    </section>

    <nav class="tabs">
      <button :class="{ active: tab === 'profile' }" type="button" @click="tab = 'profile'">画像</button>
      <button :class="{ active: tab === 'tags' }" type="button" @click="tab = 'tags'">标签</button>
      <button class="disabled" type="button" disabled>建议（二期）</button>
      <button class="disabled" type="button" disabled>日程（三期）</button>
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
      <h2>标签</h2>
      <ul class="list">
        <li v-for="t in tags?.active || []" :key="t.customer_tag_id">
          <div>
            <strong>{{ t.name }}</strong>
            <p class="muted">{{ t.sop_text || '无 SOP' }}</p>
          </div>
          <button type="button" @click="removeTag(t.customer_tag_id)">移除</button>
        </li>
      </ul>
      <p class="muted">手工添加可在后台标签体系创建后，用接口 POST /sidebar/tags。</p>
    </section>
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
.chip {
  display: inline-block;
  background: #eef4ff;
  color: #3538cd;
  border-radius: 999px;
  padding: 2px 10px;
  margin: 2px 4px 2px 0;
  font-size: 12px;
}
.tabs button {
  border: 1px solid #d0d5dd;
  background: #fff;
  border-radius: 8px;
  padding: 6px 10px;
}
.tabs button.active { background: #1f2a37; color: #fff; }
.tabs button.disabled { opacity: 0.45; }
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
