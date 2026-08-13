<script setup lang="ts">
import { computed, ref } from 'vue'
import EmptyState from '../shell/EmptyState.vue'

const props = defineProps<{
  profile: any
  generating?: boolean
}>()

const emit = defineEmits<{
  generate: []
  confirm: [mode: 'all' | 'discard']
  'confirm-field': [field: string]
  'patch-field': [field: string, value: unknown]
}>()

const draft = computed(() => props.profile?.draft)
const confirmed = computed(() => props.profile?.confirmed)

const SECTIONS: { key: string; title: string }[] = [
  { key: 'basic_info', title: '基本信息' },
  { key: 'study_info', title: '学情' },
  { key: 'prefer_info', title: '偏好' },
  { key: 'timeline', title: '时间线' },
]

type TimelineRow = { date: string; text: string }

/** 当前正在编辑的分区 key；null 表示只读 */
const editingKey = ref<string | null>(null)
/** 对象类分区：可编辑的键值行 */
const editRows = ref<{ k: string; v: string }[]>([])
/** 时间线结构化行 */
const editTimeline = ref<TimelineRow[]>([])
const editError = ref('')

function entriesOf(obj: any): { k: string; v: string }[] {
  if (obj == null) return []
  if (typeof obj !== 'object') return [{ k: '值', v: String(obj) }]
  if (Array.isArray(obj)) {
    return obj.map((item, i) => ({
      k: `#${i + 1}`,
      v: formatTimelineItem(item),
    }))
  }
  return Object.entries(obj).map(([k, v]) => ({
    k,
    v: v == null ? '—' : typeof v === 'object' ? JSON.stringify(v) : String(v),
  }))
}

function formatTimelineItem(item: unknown): string {
  if (item == null) return '—'
  if (typeof item === 'string') return item
  if (typeof item === 'object') {
    const o = item as Record<string, unknown>
    const date = o.date ?? o.time ?? o.at
    const text = o.text ?? o.event ?? o.title ?? o.desc
    if (date || text) {
      return [date, text].filter((x) => x != null && String(x).trim()).join(' · ')
    }
    return JSON.stringify(item)
  }
  return String(item)
}

function normalizeTimeline(raw: unknown): TimelineRow[] {
  if (!Array.isArray(raw) || !raw.length) return [{ date: '', text: '' }]
  return raw.map((item) => {
    if (typeof item === 'string') return { date: '', text: item }
    if (item && typeof item === 'object') {
      const o = item as Record<string, unknown>
      return {
        date: String(o.date ?? o.time ?? o.at ?? ''),
        text: String(o.text ?? o.event ?? o.title ?? o.desc ?? ''),
      }
    }
    return { date: '', text: String(item ?? '') }
  })
}

function hasContent(obj: any): boolean {
  return entriesOf(obj).length > 0
}

function fieldStatus(key: string): string {
  const st = draft.value?.field_status?.[key]
  if (typeof st === 'string' && st) return st
  return 'draft'
}

function fieldStatusLabel(key: string): string {
  const map: Record<string, string> = {
    draft: '待确认',
    confirmed: '已确认',
    pending: '待处理',
  }
  const st = fieldStatus(key)
  return map[st] || st
}

function draftStatusLabel(status?: string): string {
  const map: Record<string, string> = {
    draft: '草稿',
    partial_confirmed: '部分已确认',
    merged: '已合并',
  }
  const s = status || 'draft'
  return map[s] || s
}

/** 草稿里尚未确认、仍待处理的分区 */
const pendingSections = computed(() =>
  SECTIONS.filter((sec) => fieldStatus(sec.key) !== 'confirmed'),
)

/** 已生效画像：只展示有内容的分区 */
const confirmedSections = computed(() =>
  SECTIONS.filter((sec) => hasContent(confirmed.value?.[sec.key])),
)

const confirmedTitles = computed(() => confirmedSections.value.map((s) => s.title))

function startEdit(key: string) {
  editError.value = ''
  const raw = draft.value?.[key]
  editingKey.value = key
  if (key === 'timeline') {
    editTimeline.value = normalizeTimeline(raw)
    editRows.value = []
    return
  }
  const obj = raw && typeof raw === 'object' && !Array.isArray(raw) ? raw : {}
  editRows.value = Object.entries(obj).map(([k, v]) => ({
    k,
    v: v == null ? '' : typeof v === 'object' ? JSON.stringify(v) : String(v),
  }))
  if (!editRows.value.length) {
    editRows.value = [{ k: '', v: '' }]
  }
  editTimeline.value = []
}

function cancelEdit() {
  editingKey.value = null
  editRows.value = []
  editTimeline.value = []
  editError.value = ''
}

function addRow() {
  editRows.value.push({ k: '', v: '' })
}

function removeRow(idx: number) {
  editRows.value.splice(idx, 1)
}

function addTimelineRow() {
  editTimeline.value.push({ date: '', text: '' })
}

function removeTimelineRow(idx: number) {
  editTimeline.value.splice(idx, 1)
  if (!editTimeline.value.length) editTimeline.value = [{ date: '', text: '' }]
}

/** 把输入字符串尽量还原成原类型（布尔/数字/JSON/纯文本） */
function coerceValue(text: string): unknown {
  const t = text.trim()
  if (t === '') return ''
  if (t === 'true') return true
  if (t === 'false') return false
  if (t === 'null') return null
  if (/^-?\d+(\.\d+)?$/.test(t)) return Number(t)
  if (
    (t.startsWith('{') && t.endsWith('}')) ||
    (t.startsWith('[') && t.endsWith(']'))
  ) {
    try {
      return JSON.parse(t)
    } catch {
      return text
    }
  }
  return text
}

function buildValue(key: string): unknown {
  if (key === 'timeline') {
    return editTimeline.value
      .map((r) => ({
        date: r.date.trim() || null,
        text: r.text.trim(),
      }))
      .filter((r) => r.text)
  }
  const out: Record<string, unknown> = {}
  for (const row of editRows.value) {
    const k = row.k.trim()
    if (!k) continue
    out[k] = coerceValue(row.v)
  }
  return out
}

function saveEdit() {
  const key = editingKey.value
  if (!key || !draft.value) return
  editError.value = ''
  try {
    const value = buildValue(key)
    if (key === 'timeline' && Array.isArray(value) && !value.length) {
      editError.value = '请至少填写一条时间线事件'
      return
    }
    emit('patch-field', key, value)
    cancelEdit()
  } catch (e: any) {
    editError.value = e?.message || '内容格式不正确'
  }
}

function onConfirmField(key: string) {
  emit('confirm-field', key)
}

function onDiscard() {
  const titles = confirmedTitles.value
  const msg = titles.length
    ? `将丢弃未确认的草稿内容。\n已生效的「${titles.join('、')}」将保留，不会撤销。\n\n确定丢弃剩余草稿？`
    : '整份 AI 草稿将删除；正式画像保持不变（若本来没有则仍为空）。\n\n确定丢弃？'
  if (!window.confirm(msg)) return
  emit('confirm', 'discard')
}
</script>

<template>
  <section class="panel">
    <div class="title-row">
      <h2>客户画像 <em class="ai-badge">AI 建议</em></h2>
      <button
        type="button"
        class="primary"
        :class="{ 'is-loading': generating }"
        :disabled="generating"
        @click="emit('generate')"
      >
        {{ generating ? '生成中…' : '生成画像' }}
      </button>
    </div>

    <p class="hint">
      确认分区后立即写入正式画像；丢弃剩余草稿不会撤销已确认分区。
    </p>

    <div v-if="draft">
      <p class="muted">
        置信度 {{ draft.confidence ?? '—' }} ·
        状态 {{ draftStatusLabel(draft.status) }} ·
        来源 {{ (draft.sources || []).map((s: any) => s.label || s.type).join(' / ') || '—' }}
      </p>

      <h3 class="sub">待确认草稿（{{ pendingSections.length }}/4）</h3>
      <EmptyState
        v-if="!pendingSections.length"
        title="草稿各分区均已生效。"
        hint="可刷新查看下方「已生效画像」。"
      />

      <div v-for="sec in pendingSections" :key="sec.key" class="field-card">
        <h4>
          <span>
            {{ sec.title }}
            <em class="st">{{ fieldStatusLabel(sec.key) }}</em>
          </span>
          <span v-if="editingKey !== sec.key" class="sec-actions">
            <button type="button" @click="startEdit(sec.key)">修改</button>
            <button type="button" class="primary" @click="onConfirmField(sec.key)">
              确认并生效
            </button>
          </span>
        </h4>

        <div v-if="editingKey === sec.key" class="edit-box">
          <template v-if="sec.key === 'timeline'">
            <p class="muted tip">按「日期 + 事件」编辑，无需手写 JSON。</p>
            <div v-for="(row, idx) in editTimeline" :key="idx" class="tl-row">
              <input v-model="row.date" placeholder="日期（可选）" class="date-input" />
              <input v-model="row.text" placeholder="事件说明" class="v-input" />
              <button type="button" class="ghost" @click="removeTimelineRow(idx)">删</button>
            </div>
            <button type="button" class="ghost" @click="addTimelineRow">+ 添加事件</button>
          </template>
          <template v-else>
            <div v-for="(row, idx) in editRows" :key="idx" class="edit-row">
              <input v-model="row.k" placeholder="字段名" class="k-input" />
              <input v-model="row.v" placeholder="值" class="v-input" />
              <button type="button" class="ghost" @click="removeRow(idx)">删</button>
            </div>
            <button type="button" class="ghost" @click="addRow">+ 添加字段</button>
          </template>
          <p v-if="editError" class="err">{{ editError }}</p>
          <div class="edit-actions">
            <button type="button" class="primary" @click="saveEdit">保存修改</button>
            <button type="button" @click="cancelEdit">取消</button>
          </div>
        </div>

        <template v-else>
          <div v-if="entriesOf(draft[sec.key]).length">
            <div v-for="row in entriesOf(draft[sec.key])" :key="row.k" class="field-row">
              <span class="k">{{ row.k }}</span>
              <span class="v">{{ row.v }}</span>
            </div>
          </div>
          <p v-else class="muted">暂无</p>
        </template>
      </div>

      <div v-if="pendingSections.length" class="actions">
        <button type="button" class="primary" @click="emit('confirm', 'all')">
          全部确认并生效
        </button>
        <button type="button" @click="onDiscard">丢弃剩余草稿</button>
      </div>
      <details class="adv">
        <summary>高级 · 原始 JSON</summary>
        <pre>{{ JSON.stringify(draft, null, 2) }}</pre>
      </details>
    </div>
    <EmptyState
      v-else
      title="暂无 AI 草稿。"
      hint="可在会话后点击「生成画像」。"
    />

    <h3>已生效画像</h3>
    <div v-if="confirmedSections.length" class="field-card">
      <div v-for="sec in confirmedSections" :key="'c-' + sec.key" class="confirmed-block">
        <strong>{{ sec.title }}</strong>
        <div v-for="row in entriesOf(confirmed[sec.key])" :key="row.k" class="field-row">
          <span class="k">{{ row.k }}</span>
          <span class="v">{{ row.v }}</span>
        </div>
      </div>
    </div>
    <EmptyState v-else title="尚无已生效画像" hint="确认草稿分区后会出现在这里。" />
  </section>
</template>

<style scoped>
.panel { padding: 4px 0; }
.title-row, .actions, .edit-actions, .sec-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
h2 { margin: 0; font-size: 1.05rem; }
h3, .sub { margin: 14px 0 6px; font-size: 0.95rem; }
.hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.45;
}
.confirmed-block { margin-bottom: 10px; }
.st {
  margin-left: 6px;
  font-style: normal;
  font-size: 11px;
  font-weight: 500;
  color: var(--ai);
  background: var(--ai-soft);
  padding: 1px 6px;
  border-radius: 999px;
}
.edit-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 4px;
}
.edit-row, .tl-row {
  display: grid;
  gap: 6px;
  align-items: center;
}
.edit-row {
  grid-template-columns: minmax(72px, 0.4fr) 1fr auto;
}
.tl-row {
  grid-template-columns: minmax(100px, 0.35fr) 1fr auto;
}
.k-input, .v-input, .date-input {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 8px;
  background: #fff;
  color: var(--ink);
}
.tip { margin: 0; font-size: 12px; }
.err { margin: 0; color: var(--danger); font-size: 12px; }
.adv { margin-top: 10px; }
.adv summary { cursor: pointer; color: var(--muted); font-size: 12px; }
.adv pre {
  font-size: 11px;
  overflow: auto;
  max-height: 200px;
  background: #f8fafc;
  padding: 8px;
  border-radius: 8px;
}
</style>
