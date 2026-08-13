<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import EmptyState from '../components/EmptyState.vue'
import { useAuth } from '../composables/useAuth'
import { canWriteCustomers } from '../nav'

const route = useRoute()
const router = useRouter()
const { api, role } = useAuth()

const detail = ref<any>(null)
const users = ref<any[]>([])
const orgs = ref<any[]>([])
const error = ref('')
const flash = ref('')
const loading = ref(true)
const editing = ref(false)
const writable = computed(() => canWriteCustomers(role.value))

const editForm = ref({
  parent_name: '',
  student_name: '',
  grade: '',
  school: '',
  stage: '',
  owner_user_id: '' as string | number | '',
  org_id: '' as string | number | '',
  remark: '',
})
const csText = ref('')

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

function syncEditForm() {
  const c = detail.value?.customer
  if (!c) return
  editForm.value = {
    parent_name: c.parent_name || '',
    student_name: c.student_name || '',
    grade: c.grade || '',
    school: c.school || '',
    stage: c.stage || '',
    owner_user_id: c.owner_user_id ?? '',
    org_id: c.org_id ?? '',
    remark: c.remark || '',
  }
  csText.value = detail.value?.cs_summary?.summary_text || ''
}

async function loadMeta() {
  if (role.value === 'advisor') return
  try {
    const [u, o] = await Promise.all([
      api('/admin/users?page=1&page_size=100&role=advisor'),
      role.value === 'admin' || role.value === 'regional'
        ? api('/admin/orgs')
        : Promise.resolve({ items: [] }),
    ])
    users.value = u?.items || []
    orgs.value = o?.items || []
  } catch {
    users.value = []
    orgs.value = []
  }
}

async function load() {
  if (!customerId.value) return
  loading.value = true
  error.value = ''
  try {
    detail.value = await api(`/admin/customers/${customerId.value}`)
    syncEditForm()
  } catch (e: any) {
    error.value = e?.message || '加载失败'
    detail.value = null
  } finally {
    loading.value = false
  }
}

async function saveCustomer() {
  try {
    await api(`/admin/customers/${customerId.value}`, {
      method: 'PATCH',
      body: JSON.stringify({
        parent_name: editForm.value.parent_name.trim(),
        student_name: editForm.value.student_name.trim() || null,
        grade: editForm.value.grade.trim() || null,
        school: editForm.value.school.trim() || null,
        stage: editForm.value.stage || null,
        owner_user_id:
          editForm.value.owner_user_id === ''
            ? null
            : Number(editForm.value.owner_user_id),
        org_id: editForm.value.org_id === '' ? null : Number(editForm.value.org_id),
        remark: editForm.value.remark.trim() || null,
      }),
    })
    flash.value = '客户资料已保存'
    editing.value = false
    await load()
  } catch (e: any) {
    flash.value = e?.message || '保存失败'
  }
}

async function saveCsSummary() {
  try {
    await api(`/admin/customers/${customerId.value}/cs-summary`, {
      method: 'PUT',
      body: JSON.stringify({ summary_text: csText.value }),
    })
    flash.value = '客服摘要已保存'
    await load()
  } catch (e: any) {
    flash.value = e?.message || '摘要保存失败'
  }
}

async function removeCustomer() {
  if (!window.confirm('确认软删除该客户？删除后列表将不再显示。')) return
  try {
    await api(`/admin/customers/${customerId.value}`, { method: 'DELETE' })
    void router.push({ name: 'customers' })
  } catch (e: any) {
    flash.value = e?.message || '删除失败'
  }
}

watch(customerId, () => {
  void load()
})

onMounted(async () => {
  await loadMeta()
  await load()
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
          <p v-if="flash" class="muted">{{ flash }}</p>
        </div>
        <div v-if="writable" class="hero-actions">
          <button type="button" @click="editing = !editing">
            {{ editing ? '取消编辑' : '编辑资料' }}
          </button>
          <button type="button" @click="removeCustomer">删除客户</button>
        </div>
      </header>

      <form v-if="editing && writable" class="card form" @submit.prevent="saveCustomer">
        <strong>编辑客户资料</strong>
        <label>家长 <input v-model="editForm.parent_name" required /></label>
        <label>学员 <input v-model="editForm.student_name" /></label>
        <label>年级 <input v-model="editForm.grade" /></label>
        <label>学校 <input v-model="editForm.school" /></label>
        <label>
          学段
          <select v-model="editForm.stage">
            <option value="">—</option>
            <option value="primary">小学</option>
            <option value="junior">初中</option>
            <option value="senior">高中</option>
          </select>
        </label>
        <label v-if="role !== 'advisor'">
          负责人
          <select v-model="editForm.owner_user_id">
            <option value="">—</option>
            <option v-for="u in users" :key="u.id" :value="u.id">{{ u.name }}</option>
          </select>
        </label>
        <label v-if="role === 'admin'">
          组织
          <select v-model="editForm.org_id">
            <option value="">—</option>
            <option v-for="o in orgs" :key="o.id" :value="o.id">{{ o.name }}</option>
          </select>
        </label>
        <label>备注 <textarea v-model="editForm.remark" rows="2" /></label>
        <button type="submit" class="primary">保存资料</button>
      </form>

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
          <template v-if="writable">
            <textarea v-model="csText" rows="4" class="cs" placeholder="填写售后/跟进摘要…" />
            <button type="button" class="primary cs-btn" @click="saveCsSummary">保存摘要</button>
          </template>
          <p v-else-if="detail.cs_summary?.summary_text" class="summary">
            {{ detail.cs_summary.summary_text }}
          </p>
          <EmptyState v-else title="暂无客服摘要" />

          <p class="sec-label">标签</p>
          <div v-if="(detail.tags || []).length" class="chips">
            <span v-for="t in detail.tags" :key="t.customer_tag_id || t.id" class="chip">
              {{ t.name }}
            </span>
          </div>
          <EmptyState v-else title="暂无标签" hint="标签挂载请在侧栏操作。" />

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
          <EmptyState v-else title="暂无订单" hint="可在「订单」页新建。" />

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
.hero {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  flex-wrap: wrap;
}
.hero h2 { margin: 0; font-size: 1.2rem; font-family: var(--font-display); }
.meta { margin: 6px 0 0; }
.hero-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.form {
  display: grid;
  gap: 8px;
  margin-top: 12px;
  max-width: 560px;
}
.form label {
  display: grid;
  gap: 4px;
  font-size: 13px;
  color: var(--muted);
}
.form input,
.form select,
.form textarea,
.cs {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 8px;
  color: var(--ink);
  width: 100%;
  font: inherit;
}
.cs-btn { margin-top: 6px; }
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
.timeline li.out .dir { color: var(--accent); }
.timeline .time { font-size: 11px; color: var(--muted); }
.muted { color: var(--muted); }
@media (max-width: 800px) {
  .split { grid-template-columns: 1fr; }
}
</style>
