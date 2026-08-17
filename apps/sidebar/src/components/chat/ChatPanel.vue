<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { Mic, RefreshCw, Send } from '@lucide/vue'
import UiIcon from '../UiIcon.vue'
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

export type ChatCustomer = {
  id: number
  parent_name?: string | null
  student_name?: string | null
  external_id?: string | null
  last_preview?: string | null
}

const props = defineProps<{
  api: ApiFn
  customerId: number | null
  customers?: ChatCustomer[]
}>()

const emit = defineEmits<{
  status: [msg: string]
  refreshed: []
  stale: []
  'select-customer': [id: number]
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
const localCustomers = ref<ChatCustomer[]>([])

const sessionList = computed(() =>
  props.customers?.length ? props.customers : localCustomers.value,
)

const QUICK = [
  { label: '成绩跟不上', text: '孩子最近数学成绩下滑，想了解怎么补' },
  { label: '价格敏感', text: '想问问初二数学价格大概多少，有没有分期？' },
  { label: '时间意图', text: '下周六上午我们过来试听，记得提醒我' },
  { label: '客服请假', text: '这周孩子请假一次，能不能安排补课？' },
]

async function loadCustomers() {
  if (props.customers?.length) return
  try {
    const data = await props.api('/mock/customers')
    localCustomers.value = data?.items || []
  } catch (e: any) {
    emit('status', e?.message || '加载客户列表失败')
  }
}

function sessionLabel(c: ChatCustomer) {
  const parent = c.parent_name || '家长'
  const student = c.student_name || '—'
  return `${parent}/${student}`
}

function selectCustomer(id: number) {
  if (id === props.customerId) return
  emit('select-customer', id)
}

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
    emit('stale')
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
    emit('stale')
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

onMounted(() => {
  void loadCustomers()
})

defineExpose({ load })
</script>

<template>
  <section
    class="flex h-full min-h-[520px] overflow-hidden rounded-panel border border-line border-l-[3px] border-l-fjord bg-stone-50 shadow-soft"
  >
    <!-- Session list -->
    <aside class="flex w-[240px] shrink-0 flex-col border-r border-line bg-white">
      <header class="border-b border-line px-3 py-2.5">
        <strong class="text-sm font-semibold text-ink">会话</strong>
        <p class="mt-0.5 text-[11px] text-muted">模拟 · 不代发企微</p>
      </header>
      <ul class="m-0 flex-1 list-none overflow-auto p-0">
        <li v-if="!sessionList.length" class="px-3 py-4 text-xs text-muted">暂无客户</li>
        <li v-for="c in sessionList" :key="c.id">
          <button
            type="button"
            class="w-full border-none px-3 py-2.5 text-left transition-colors"
            :class="
              c.id === customerId
                ? 'bg-fjord-soft text-fjord'
                : 'bg-transparent text-ink hover:bg-stone-50'
            "
            @click="selectCustomer(c.id)"
          >
            <span class="block truncate text-sm font-medium">{{ sessionLabel(c) }}</span>
            <span v-if="c.last_preview" class="mt-0.5 block truncate text-[11px] text-muted">
              {{ c.last_preview }}
            </span>
          </button>
        </li>
      </ul>
    </aside>

    <!-- Chat thread -->
    <div class="flex min-w-0 flex-1 flex-col">
      <header class="flex items-center gap-2 border-b border-line bg-white px-3 py-2">
        <span class="flex-1 text-sm font-semibold text-ink">
          {{ customerId ? `客户 #${customerId}` : '请选择会话' }}
        </span>
        <button
          type="button"
          class="inline-flex items-center gap-1 rounded-control border border-line bg-white px-2 py-1 text-xs text-muted hover:bg-stone-50 disabled:opacity-50"
          :disabled="!customerId"
          @click="load"
        >
          <UiIcon :icon="RefreshCw" :size="14" />
          刷新
        </button>
      </header>

      <div ref="listEl" class="flex-1 overflow-auto px-3 py-3">
        <p v-if="!customerId" class="text-center text-sm text-muted">请从左侧选择客户</p>
        <p v-else-if="!messages.length" class="text-center text-sm text-muted">
          暂无消息。发送一条或点快捷话术开始。
        </p>
        <div
          v-for="m in messages"
          :key="m.id"
          class="mb-2.5 flex"
          :class="m.direction === 'out' ? 'justify-end' : 'justify-start'"
        >
          <div
            class="max-w-[85%] rounded-md px-2.5 py-2 text-sm shadow-soft"
            :class="
              m.direction === 'out'
                ? 'bg-fjord text-white'
                : 'border border-line bg-white text-ink'
            "
          >
            <div v-if="m.msg_type === 'voice'">
              <span
                class="mb-1 inline-block rounded px-1.5 py-px text-[11px]"
                :class="
                  m.direction === 'out'
                    ? 'bg-white/20 text-white'
                    : 'bg-fjord-soft text-fjord'
                "
              >
                语音
              </span>
              <p v-if="m.asr_text" class="m-0 whitespace-pre-wrap break-words">
                已转写：{{ m.asr_text }}
              </p>
              <p v-else class="m-0 text-muted">{{ m.content || '[语音]' }}</p>
            </div>
            <p v-else class="m-0 whitespace-pre-wrap break-words">{{ m.content }}</p>
            <div
              class="mt-1.5 flex flex-wrap gap-2 text-[11px]"
              :class="m.direction === 'out' ? 'text-white/80' : 'text-muted'"
            >
              <span>{{ m.direction === 'in' ? '家长' : '顾问' }}</span>
              <span v-if="m.is_mock">模拟</span>
              <span v-if="m.msg_time">{{ m.msg_time.replace('T', ' ').replace('Z', '') }}</span>
            </div>
            <div class="mt-1.5 flex flex-wrap gap-1.5">
              <button
                type="button"
                class="rounded-control px-2 py-px text-[11px]"
                :class="
                  m.direction === 'out'
                    ? 'border border-white/35 bg-white/15 text-white'
                    : 'border border-line bg-stone-50 text-muted'
                "
                @click="copyBubble(m)"
              >
                {{ copyHintId === m.id ? '已复制' : '复制本句' }}
              </button>
              <template v-if="m.direction === 'in'">
                <button
                  type="button"
                  class="rounded-control border border-line bg-stone-50 px-2 py-px text-[11px] text-muted"
                  title="基于整段会话生成，非仅本句"
                  @click="onUseReply"
                >
                  生成话术（全会话）
                </button>
                <button
                  type="button"
                  class="rounded-control border border-line bg-stone-50 px-2 py-px text-[11px] text-muted"
                  title="基于整段会话识别，非仅本句"
                  @click="onUseSchedule"
                >
                  生成日程（全会话）
                </button>
              </template>
            </div>
          </div>
        </div>
      </div>

      <div class="flex flex-wrap gap-1.5 border-t border-line bg-white px-3 py-2">
        <button
          v-for="q in QUICK"
          :key="q.label"
          type="button"
          class="cursor-pointer border-none bg-transparent p-0 text-xs text-fjord underline-offset-2 hover:underline disabled:opacity-50"
          :disabled="!customerId || busy"
          @click="sendQuick(q.text)"
        >
          {{ q.label }}
        </button>
      </div>

      <footer class="sticky bottom-0 flex items-center gap-1.5 border-t border-line bg-white px-3 py-2.5">
        <div class="flex shrink-0 gap-0.5 rounded-control border border-line p-0.5">
          <button
            type="button"
            class="rounded-control px-2 py-1 text-xs"
            :class="
              direction === 'in'
                ? 'bg-fjord text-white'
                : 'bg-transparent text-muted hover:bg-stone-50'
            "
            @click="direction = 'in'"
          >
            家长
          </button>
          <button
            type="button"
            class="rounded-control px-2 py-1 text-xs"
            :class="
              direction === 'out'
                ? 'bg-fjord text-white'
                : 'bg-transparent text-muted hover:bg-stone-50'
            "
            @click="direction = 'out'"
          >
            顾问
          </button>
        </div>
        <input
          v-model="draft"
          placeholder="输入模拟消息…"
          class="min-w-0 flex-1 rounded-control border border-line px-2.5 py-2"
          :disabled="!customerId || busy"
          @keyup.enter="send"
        />
        <button
          type="button"
          class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-control bg-fjord text-white hover:opacity-90 disabled:opacity-50"
          :disabled="!customerId || busy"
          title="发送"
          @click="send"
        >
          <UiIcon :icon="Send" :size="18" />
        </button>
        <button
          type="button"
          class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-control border border-line bg-white text-muted hover:bg-stone-50 disabled:opacity-50"
          :disabled="!customerId || asrBusy"
          title="演示：用输入框内容作提示，调用 Fake ASR 写入语音消息"
          @click="simulateVoice"
        >
          <UiIcon :icon="Mic" :size="18" />
        </button>
      </footer>
    </div>
  </section>
</template>
