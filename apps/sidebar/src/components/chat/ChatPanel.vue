<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { ApiFn } from '../../composables/useApi'

export type ChatMessage = {
  id: number
  direction: 'in' | 'out'
  msg_type: string
  content: string | null
  asr_text?: string | null
  msg_time?: string | null
  is_mock?: boolean
}

const props = defineProps<{
  api: ApiFn
  customerId: number | null
}>()

const emit = defineEmits<{
  status: [msg: string]
  refreshed: []
  'use-reply': []
  'use-schedule': []
  'goto-tab': [tab: 'profile' | 'suggest' | 'tags' | 'schedule']
}>()

const messages = ref<ChatMessage[]>([])
const draft = ref('')
const direction = ref<'in' | 'out'>('in')
const busy = ref(false)
const asrBusy = ref(false)
const listEl = ref<HTMLElement | null>(null)
const copyHintId = ref<number | null>(null)

const QUICK = [
  { label: '成绩跟不上', text: '孩子最近数学成绩下滑，想了解怎么补' },
  { label: '价格敏感', text: '想问问初二数学价格大概多少，有没有分期？' },
  { label: '时间意图', text: '下周六上午我们过来试听，记得提醒我' },
  { label: '客服请假', text: '这周孩子请假一次，能不能安排补课？' },
]

async function load() {
  if (!props.customerId) {
    messages.value = []
    return
  }
  const data = await props.api(
    `/sidebar/messages?customer_id=${props.customerId}&limit=100`,
  )
  messages.value = data?.items || []
  await nextTick()
  if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
}

async function send() {
  if (!props.customerId || !draft.value.trim() || busy.value) return
  busy.value = true
  try {
    await props.api('/mock/messages', {
      method: 'POST',
      body: JSON.stringify({
        customer_id: props.customerId,
        direction: direction.value,
        content: draft.value.trim(),
        msg_type: 'text',
      }),
    })
    draft.value = ''
    emit('status', '已写入模拟消息')
    await load()
    emit('refreshed')
  } catch (e: any) {
    emit('status', e?.message || '发送失败')
  } finally {
    busy.value = false
  }
}

async function sendQuick(text: string) {
  draft.value = text
  direction.value = 'in'
  await send()
}

async function simulateVoice() {
  if (!props.customerId || asrBusy.value) return
  asrBusy.value = true
  emit('status', '语音转写中…')
  try {
    const hint = draft.value.trim() || '下周周六上午方便来试听吗'
    const data = await props.api('/sidebar/asr/transcribe', {
      method: 'POST',
      body: JSON.stringify({
        customer_id: props.customerId,
        audio_ref: `mock://voice/${Date.now()}.wav`,
        content_hint: hint,
        create_message: true,
      }),
    })
    draft.value = ''
    emit('status', data?.asr_text ? `已转写：${data.asr_text}` : '转写完成')
    await load()
    emit('refreshed')
  } catch (e: any) {
    emit('status', e?.message || '转写失败，不阻断文本建议')
  } finally {
    asrBusy.value = false
  }
}

function bubbleText(m: ChatMessage): string {
  if (m.msg_type === 'voice') return (m.asr_text || m.content || '').trim()
  return (m.content || '').trim()
}

async function copyBubble(m: ChatMessage) {
  const text = bubbleText(m)
  if (!text) {
    emit('status', '该消息无可复制文本')
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    copyHintId.value = m.id
    emit('status', '已复制本句（请到企微手动粘贴）')
    window.setTimeout(() => {
      if (copyHintId.value === m.id) copyHintId.value = null
    }, 2000)
  } catch {
    emit('status', '复制失败，请手动选中文案')
  }
}

function onUseReply() {
  emit('goto-tab', 'suggest')
  emit('use-reply')
}

function onUseSchedule() {
  emit('goto-tab', 'schedule')
  emit('use-schedule')
}

watch(
  () => props.customerId,
  () => {
    void load()
  },
  { immediate: true },
)

defineExpose({ load })
</script>

<template>
  <section class="chat">
    <header class="chat-head">
      <strong>模拟会话</strong>
      <span class="muted">仅演示 · 不代发企微</span>
      <button type="button" class="ghost" :disabled="!customerId" @click="load">刷新</button>
    </header>

    <div ref="listEl" class="list">
      <p v-if="!customerId" class="empty-hint">请先选择客户</p>
      <p v-else-if="!messages.length" class="empty-hint">暂无消息。发送一条或点快捷话术开始。</p>
      <div
        v-for="m in messages"
        :key="m.id"
        class="row"
        :class="m.direction === 'out' ? 'out' : 'in'"
      >
        <div class="bubble">
          <div v-if="m.msg_type === 'voice'" class="voice">
            <span class="voice-label">语音</span>
            <p v-if="m.asr_text" class="asr">已转写：{{ m.asr_text }}</p>
            <p v-else class="muted">{{ m.content || '[语音]' }}</p>
          </div>
          <p v-else class="text">{{ m.content }}</p>
          <div class="meta">
            <span>{{ m.direction === 'in' ? '家长' : '顾问' }}</span>
            <span v-if="m.is_mock">模拟</span>
            <span v-if="m.msg_time">{{ m.msg_time.replace('T', ' ').replace('Z', '') }}</span>
          </div>
          <div class="bubble-actions">
            <button type="button" @click="copyBubble(m)">
              {{ copyHintId === m.id ? '已复制' : '复制本句' }}
            </button>
            <template v-if="m.direction === 'in'">
              <button type="button" title="基于整段会话生成，非仅本句" @click="onUseReply">
                生成话术（全会话）
              </button>
              <button type="button" title="基于整段会话识别，非仅本句" @click="onUseSchedule">
                生成日程（全会话）
              </button>
            </template>
          </div>
        </div>
      </div>
    </div>

    <div class="quick">
      <button
        v-for="q in QUICK"
        :key="q.label"
        type="button"
        :disabled="!customerId || busy"
        @click="sendQuick(q.text)"
      >
        {{ q.label }}
      </button>
    </div>

    <footer class="composer">
      <select v-model="direction">
        <option value="in">家长</option>
        <option value="out">顾问</option>
      </select>
      <input
        v-model="draft"
        placeholder="输入模拟消息…"
        :disabled="!customerId || busy"
        @keyup.enter="send"
      />
      <button type="button" class="primary" :disabled="!customerId || busy" @click="send">
        发送
      </button>
      <button
        type="button"
        title="演示：用输入框内容作提示，调用 Fake ASR 写入语音消息"
        :disabled="!customerId || asrBusy"
        @click="simulateVoice"
      >
        {{ asrBusy ? '转写中…' : '语音（模拟）' }}
      </button>
    </footer>
  </section>
</template>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 420px;
  background: var(--bg-chat);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}
.chat-head {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 10px 12px;
  background: var(--surface);
  border-bottom: 1px solid var(--line);
}
.list {
  flex: 1;
  overflow: auto;
  padding: 12px;
}
.row {
  display: flex;
  margin-bottom: 10px;
}
.row.in { justify-content: flex-start; }
.row.out { justify-content: flex-end; }
.bubble {
  max-width: 85%;
  padding: 8px 10px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: var(--in-bubble);
  box-shadow: var(--shadow);
}
.row.out .bubble {
  background: var(--out-bubble);
  border-color: var(--out-bubble);
  color: #fff;
}
.row.out .muted,
.row.out .meta { color: rgba(255, 255, 255, 0.8); }
.text { margin: 0; white-space: pre-wrap; word-break: break-word; font-size: 14px; }
.voice-label {
  display: inline-block;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--ai-soft);
  color: var(--ai);
  margin-bottom: 4px;
}
.row.out .voice-label { background: rgba(255,255,255,0.2); color: #fff; }
.asr { margin: 4px 0 0; font-size: 13px; }
.meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 11px;
  color: var(--muted);
  margin-top: 6px;
}
.bubble-actions {
  display: flex;
  gap: 6px;
  margin-top: 6px;
  flex-wrap: wrap;
}
.bubble-actions button {
  font-size: 11px;
  padding: 2px 8px;
}
.row.out .bubble-actions button {
  background: rgba(255,255,255,0.15);
  border-color: rgba(255,255,255,0.35);
  color: #fff;
}
.quick {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  padding: 8px 12px;
  background: var(--surface);
  border-top: 1px solid var(--line);
}
.quick button { font-size: 12px; padding: 4px 8px; }
.composer {
  display: flex;
  gap: 6px;
  padding: 10px 12px;
  background: var(--surface);
  border-top: 1px solid var(--line);
  align-items: center;
}
.composer input {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 10px;
}
.composer select {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px;
}
</style>
