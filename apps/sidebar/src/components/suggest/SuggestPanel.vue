<script setup lang="ts">
import { computed, ref, shallowRef, watch } from 'vue'

export type ReplyOutcome = {
  kind: 'copied' | 'adopted' | 'rejected' | 'edit_adopted'
  text?: string
  suggestionId: number
}

const props = defineProps<{
  reply: any
  replyScene: 'sales' | 'cs'
  replyBusy?: boolean
  lastAsr?: string | null
  /** 采纳/拒绝/编辑采纳后的结果态；复制也可带轻结果 */
  outcome?: ReplyOutcome | null
}>()

const emit = defineEmits<{
  'update:replyScene': [v: 'sales' | 'cs']
  suggest: []
  feedback: [action: 'copy' | 'adopt' | 'reject' | 'edit_adopt', text?: string]
  'clear-outcome': []
  status: [msg: string]
}>()

const editing = shallowRef(false)
const draftText = ref('')
const displayPrimary = ref('')
const localCopied = shallowRef(false)

const sceneLabel = computed(() => (props.replyScene === 'cs' ? '客服' : '销售'))

const basisLine = computed(() => {
  const parts = [`近 10 条会话`, `客户画像`, `${sceneLabel.value}场景模板`]
  if (props.reply?.based_on_asr || props.lastAsr) parts.push('含语音转写')
  return `生成依据：${parts.join(' · ')}`
})

const outcomeTitle = computed(() => {
  switch (props.outcome?.kind) {
    case 'adopted':
      return '已标记有用'
    case 'rejected':
      return '已标记不适用'
    case 'edit_adopted':
      return '已按编辑稿标记有用'
    case 'copied':
      return '已复制到剪贴板'
    default:
      return ''
  }
})

const outcomeHint = computed(() => {
  switch (props.outcome?.kind) {
    case 'adopted':
    case 'edit_adopted':
      return '仅记录反馈，不会代发企微。可将下方文案自行粘贴发送。'
    case 'rejected':
      return '本条建议已从「待处理」移除。可再生成新建议。'
    case 'copied':
      return '请到企微手动粘贴发送；系统不代发。'
    default:
      return ''
  }
})

const showResultCard = computed(
  () =>
    !!props.outcome &&
    (props.outcome.kind === 'adopted' ||
      props.outcome.kind === 'rejected' ||
      props.outcome.kind === 'edit_adopted'),
)

watch(
  () => props.reply?.primary,
  (v) => {
    displayPrimary.value = typeof v === 'string' ? v : ''
    editing.value = false
    localCopied.value = false
  },
  { immediate: true },
)

watch(
  () => props.reply?.suggestion_id,
  () => {
    localCopied.value = false
  },
)

function startEdit() {
  draftText.value = displayPrimary.value
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  draftText.value = ''
}

function useAltAsPrimary(alt: string) {
  displayPrimary.value = alt
  editing.value = false
  localCopied.value = false
}

async function copyTextOnly(text?: string) {
  const t = (text || '').trim()
  if (!t) return
  try {
    await navigator.clipboard.writeText(t)
    localCopied.value = true
    emit('status', '已复制（请到企微手动发送，系统不代发）')
  } catch {
    emit('status', '复制失败，请手动选中文案')
  }
}

function onCopy(text?: string) {
  const t = (text ?? displayPrimary.value).trim()
  if (!t) return
  localCopied.value = true
  emit('feedback', 'copy', t)
}

function onAdopt() {
  emit('feedback', 'adopt', displayPrimary.value)
}

function onReject() {
  emit('feedback', 'reject')
}

function onEditAdopt() {
  const t = draftText.value.trim()
  if (!t) return
  emit('feedback', 'edit_adopt', t)
}

function onCopyEdited() {
  const t = draftText.value.trim()
  if (!t) return
  localCopied.value = true
  emit('feedback', 'copy', t)
}

function regenerate() {
  emit('clear-outcome')
  emit('suggest')
}
</script>

<template>
  <section class="panel">
    <div class="title-row">
      <h2>回复建议 <em class="ai-badge">AI 建议</em></h2>
      <div class="seg">
        <button
          type="button"
          :class="{ active: replyScene === 'sales' }"
          @click="emit('update:replyScene', 'sales')"
        >
          销售
        </button>
        <button
          type="button"
          :class="{ active: replyScene === 'cs' }"
          @click="emit('update:replyScene', 'cs')"
        >
          客服
        </button>
      </div>
      <button type="button" class="primary" :disabled="replyBusy" @click="regenerate">
        {{ replyBusy ? '生成中…' : reply?.primary || outcome ? '再生成' : '生成建议' }}
      </button>
    </div>

    <p class="muted tip">
      不会自动发送。主操作是「复制到企微」，再到企微手动粘贴。
    </p>
    <p class="basis">{{ basisLine }}</p>
    <p v-if="reply?.based_on_asr || lastAsr" class="asr-banner">
      含转写：{{ reply?.based_on_asr || lastAsr }}
    </p>

    <!-- 采纳 / 拒绝 / 编辑采纳后的结果卡 -->
    <div v-if="showResultCard" class="result-card" :data-kind="outcome?.kind">
      <h3>{{ outcomeTitle }}</h3>
      <p class="result-hint">{{ outcomeHint }}</p>
      <pre v-if="outcome?.text" class="script">{{ outcome.text }}</pre>
      <div class="actions">
        <button
          v-if="outcome?.text"
          type="button"
          class="primary"
          @click="copyTextOnly(outcome?.text)"
        >
          复制到企微
        </button>
        <button type="button" class="primary" :disabled="replyBusy" @click="regenerate">
          {{ replyBusy ? '生成中…' : '再生成' }}
        </button>
      </div>
    </div>

    <!-- 待处理建议 -->
    <div v-else-if="reply?.primary" class="field-card main">
      <div class="main-head">
        <h3>主建议</h3>
        <span v-if="localCopied || outcome?.kind === 'copied'" class="chip ok">已复制</span>
      </div>

      <template v-if="!editing">
        <pre class="script">{{ displayPrimary }}</pre>
        <div class="actions">
          <button type="button" class="primary" @click="onCopy()">复制到企微</button>
          <button type="button" @click="startEdit">编辑</button>
          <button type="button" @click="onAdopt">标记有用</button>
          <button type="button" class="ghost danger-btn" @click="onReject">不适用</button>
        </div>
        <p class="action-hint">
          「标记有用 / 不适用」只记反馈，不会发消息；「复制到企微」才是真正带走文案。
        </p>
      </template>

      <template v-else>
        <label class="edit-label">编辑稿（保存为「编辑后标记有用」时写入后端）</label>
        <textarea v-model="draftText" class="editor" rows="6" />
        <div class="actions">
          <button
            type="button"
            class="primary"
            :disabled="!draftText.trim()"
            @click="onCopyEdited"
          >
            复制编辑稿
          </button>
          <button
            type="button"
            :disabled="!draftText.trim()"
            @click="onEditAdopt"
          >
            标记有用（编辑稿）
          </button>
          <button type="button" class="ghost" @click="cancelEdit">取消</button>
        </div>
      </template>

      <details v-if="(reply.alternatives || []).length" class="alts" open>
        <summary>备选 {{ reply.alternatives.length }} 条</summary>
        <div v-for="(alt, i) in reply.alternatives" :key="i" class="alt-row">
          <pre class="script alt">{{ alt }}</pre>
          <div class="actions alt-actions">
            <button type="button" @click="useAltAsPrimary(alt)">设为主建议</button>
            <button type="button" class="primary" @click="onCopy(alt)">复制</button>
            <button
              type="button"
              @click="
                useAltAsPrimary(alt);
                onAdopt();
              "
            >
              标记有用
            </button>
          </div>
        </div>
      </details>
    </div>

    <div v-else class="empty-box">
      <p class="empty-hint">
        暂无待处理话术。先选场景再生成，或从会话点「生成话术（全会话）」。
      </p>
      <button type="button" class="primary" :disabled="replyBusy" @click="regenerate">
        {{ replyBusy ? '生成中…' : '生成建议' }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.panel { padding: 4px 0; }
.title-row, .actions, .seg {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
h2 { margin: 0; font-size: 1.05rem; }
h3 { margin: 0 0 8px; font-size: 0.95rem; }
.tip { margin: 8px 0 4px; }
.basis {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.45;
}
.asr-banner {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  padding: 8px 10px;
  color: #075985;
  margin: 0 0 8px;
  font-size: 13px;
}
.main { margin-top: 8px; }
.main-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.main-head h3 { margin: 0; }
.chip.ok {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
}
.script {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: var(--font-ui);
  font-size: 14px;
  line-height: 1.5;
  background: #f8fafc;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px;
}
.script.alt { font-size: 13px; }
.action-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.4;
}
.edit-label {
  display: block;
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 6px;
}
.editor {
  width: 100%;
  resize: vertical;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px;
  font: inherit;
  line-height: 1.5;
  background: #fff;
}
.alts { margin-top: 12px; }
summary { cursor: pointer; color: var(--muted); font-size: 13px; }
.alt-row {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--line);
}
.alt-actions { margin-top: 6px; }
.alt-actions button { font-size: 12px; padding: 4px 8px; }
.result-card {
  margin-top: 10px;
  padding: 12px;
  border-radius: var(--radius);
  border: 1px solid var(--line);
  background: var(--accent-soft);
}
.result-card[data-kind='rejected'] {
  background: var(--warn-soft);
  border-color: #fed7aa;
}
.result-hint {
  margin: 0 0 10px;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.45;
}
.danger-btn { color: var(--danger); }
.empty-box {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
}
</style>
