<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import EmptyState from '../components/EmptyState.vue'
import { useAuth } from '../composables/useAuth'

const route = useRoute()
const router = useRouter()
const { api } = useAuth()

const detail = ref<any>(null)
const error = ref('')
const loading = ref(true)

const customerId = computed(() => Number(route.params.id))

function entriesOf(obj: any): { k: string; v: string }[] {
  if (obj == null) return []
  if (typeof obj !== 'object') return [{ k: '值', v: String(obj) }]
  if (Array.isArray(obj)) {
    return obj.map((item, i) => ({
      k: `#${i + 1}`,
      v: typeof item === 'object' ? formatObj(item) : String(item),
    }))
  }
  return Object.entries(obj).map(([k, v]) => ({
    k,
    v: v == null ? '—' : typeof v === 'object' ? formatObj(v) : String(v),
  }))
}

function formatObj(o: Record<string, unknown> | unknown) {
  if (!o || typeof o !== 'object') return String(o)
  const rec = o as Record<string, unknown>
  if (rec.date || rec.text) {
    return [rec.date, rec.text].filter(Boolean).join(' · ')
  }
  return JSON.stringify(o)
}

const SECTIONS = [
  { key: 'basic_info', title: '基本信息' },
  { key: 'study_info', title: '学情' },
  { key: 'prefer_info', title: '偏好' },
  { key: 'timeline', title: '时间线' },
]

const confirmedBlocks = computed(() => {
  const c = detail.value?.profile?.confirmed
  if (!c) return []
  return SECTIONS.map((s) => ({
    ...s,
    rows: entriesOf(c[s.key]),
  })).filter((b) => b.rows.length)
})

const draftBlocks = computed(() => {
  const d = detail.value?.profile?.draft
  if (!d) return []
  return SECTIONS.map((s) => ({
    ...s,
    rows: entriesOf(d[s.key]),
  })).filter((b) => b.rows.length)
})

const messages = computed(() => {
  const list = detail.value?.recent_messages || []
  return [...list].reverse()
})

async function load() {
  if (!customerId.value) return
  loading.value = true
  error.value = ''
  try {
    detail.value = await api(`/admin/customers/${customerId.value}`)
  } catch (e: any) {
    error.value = e?.message || '加载失败'
    detail.value = null
  } finally {
    loading.value = false
  }
}

watch(customerId, () => {
  void load()
})

onMounted(() => {
  void load()
})
</script>

<template>
  <div>
    <button type="button" class="ghost back" @click="router.push({ name: 'customers' })">
      ← 返回客户列表
    </button>

    <p v-if="loading" class="muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" hint="无权限或不在数据范围内。" />

    <template v-else-if="detail">
      <header class="hero card">
        <div>
          <h2>
            {{ detail.customer.parent_name }}
            <span class="muted">/</span>
            {{ detail.customer.student_name || '—' }}
          </h2>
          <p class="muted meta">
            #{{ detail.customer.id }}
            · {{ detail.customer.grade || '年级未知' }}
            · {{ detail.customer.school || '学校未知' }}
            · 负责人 {{ detail.customer.owner_name || '—' }}
          </p>
        </div>
      </header>

      <div class="split">
        <aside class="col card">
          <h3>画像</h3>
          <p class="sec-label">已确认</p>
          <div v-if="confirmedBlocks.length">
            <div v-for="b in confirmedBlocks" :key="'c-' + b.key" class="block">
              <strong>{{ b.title }}</strong>
              <div v-for="row in b.rows" :key="row.k" class="row">
                <span class="k">{{ row.k }}</span>
                <span class="v">{{ row.v }}</span>
              </div>
            </div>
          </div>
          <EmptyState v-else title="尚无已确认画像" hint="顾问在侧栏确认后会出现在这里。" />

          <p class="sec-label">草稿</p>
          <div v-if="draftBlocks.length">
            <div v-for="b in draftBlocks" :key="'d-' + b.key" class="block draft">
              <strong>{{ b.title }}</strong>
              <div v-for="row in b.rows" :key="row.k" class="row">
                <span class="k">{{ row.k }}</span>
                <span class="v">{{ row.v }}</span>
              </div>
            </div>
          </div>
          <EmptyState v-else title="无进行中草稿" />
        </aside>

        <section class="col card">
          <h3>沟通与经营</h3>

          <p class="sec-label">客服摘要</p>
          <p v-if="detail.cs_summary?.summary_text" class="summary">
            {{ detail.cs_summary.summary_text }}
          </p>
          <EmptyState v-else title="暂无客服摘要" />

          <p class="sec-label">标签</p>
          <div v-if="(detail.tags || []).length" class="chips">
            <span v-for="t in detail.tags" :key="t.customer_tag_id || t.id" class="chip">
              {{ t.name }}
            </span>
          </div>
          <EmptyState v-else title="暂无标签" />

          <p class="sec-label">订单</p>
          <table v-if="(detail.orders || []).length" class="data">
            <thead>
              <tr><th>单号</th><th>课程</th><th>金额</th><th>状态</th></tr>
            </thead>
            <tbody>
              <tr v-for="o in detail.orders" :key="o.id">
                <td>{{ o.external_order_no || o.id }}</td>
                <td>{{ o.title }}</td>
                <td>{{ o.amount ?? '—' }}</td>
                <td>{{ o.status }}</td>
              </tr>
            </tbody>
          </table>
          <EmptyState v-else title="暂无订单" />

          <p class="sec-label">沟通时间线（近 30 条）</p>
          <ul v-if="messages.length" class="timeline">
            <li
              v-for="m in messages"
              :key="m.id"
              :class="m.direction === 'out' ? 'out' : 'in'"
            >
              <span class="dir">{{ m.direction === 'out' ? '顾问' : '家长' }}</span>
              <span class="body">{{ m.content || '—' }}</span>
              <span v-if="m.msg_time" class="time">{{ m.msg_time.replace('T', ' ').replace('Z', '') }}</span>
            </li>
          </ul>
          <EmptyState v-else title="暂无沟通记录" />
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.back { margin-bottom: 10px; }
.hero h2 { margin: 0; font-size: 1.2rem; font-family: var(--font-display); }
.meta { margin: 6px 0 0; }
.split {
  display: grid;
  grid-template-columns: minmax(260px, 0.9fr) minmax(300px, 1.1fr);
  gap: 12px;
  margin-top: 12px;
  align-items: start;
}
.col h3 { margin: 0 0 8px; font-size: 1rem; }
.sec-label {
  margin: 14px 0 6px;
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
}
.sec-label:first-of-type { margin-top: 0; }
.block { margin-bottom: 10px; }
.block.draft {
  padding: 8px;
  border-radius: 8px;
  background: var(--ai-soft);
}
.row {
  display: flex;
  gap: 8px;
  font-size: 13px;
  margin: 3px 0;
}
.k { color: var(--muted); min-width: 64px; flex-shrink: 0; }
.v { flex: 1; word-break: break-word; }
.summary {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
}
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  background: var(--accent-soft);
  color: var(--accent);
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 12px;
}
.timeline {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 420px;
  overflow: auto;
}
.timeline li {
  display: grid;
  gap: 2px;
  padding: 8px 0;
  border-bottom: 1px solid #eef2f6;
  font-size: 13px;
}
.timeline .dir {
  font-size: 11px;
  color: var(--muted);
}
.timeline.out .dir,
.timeline li.out .dir { color: var(--accent); }
.timeline .time { font-size: 11px; color: var(--muted); }
@media (max-width: 800px) {
  .split { grid-template-columns: 1fr; }
}
</style>
