<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Save, Trash2, X } from '@lucide/vue'
import EmptyState from '../components/EmptyState.vue'
import FlashBanner from '../components/FlashBanner.vue'
import UiIcon from '../components/UiIcon.vue'
import { useFlash } from '../composables/useFlash'
import { useAuth } from '../composables/useAuth'
import { canWriteCustomers } from '../nav'

const route = useRoute()
const router = useRouter()
const { api, role } = useAuth()
const flash = useFlash()

const detail = ref<any>(null)
const users = ref<any[]>([])
const orgs = ref<any[]>([])
const error = ref('')
const loading = ref(true)
const busy = ref(false)
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

function cancelEdit() {
  syncEditForm()
  editing.value = false
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
  if (!editForm.value.parent_name.trim()) {
    flash.err('请填写家长姓名')
    return
  }
  busy.value = true
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
    flash.ok('客户资料已保存')
    editing.value = false
    await load()
  } catch (e: any) {
    flash.err(e?.message || '保存失败')
  } finally {
    busy.value = false
  }
}

async function saveCsSummary() {
  busy.value = true
  try {
    await api(`/admin/customers/${customerId.value}/cs-summary`, {
      method: 'PUT',
      body: JSON.stringify({ summary_text: csText.value }),
    })
    flash.ok('客服摘要已保存')
    await load()
  } catch (e: any) {
    flash.err(e?.message || '摘要保存失败')
  } finally {
    busy.value = false
  }
}

async function removeCustomer() {
  const name = detail.value?.customer?.parent_name || '该客户'
  if (!window.confirm(`确认软删除客户「${name}」？删除后列表将不再显示。`)) return
  busy.value = true
  try {
    await api(`/admin/customers/${customerId.value}`, { method: 'DELETE' })
    void router.push({ name: 'customers' })
  } catch (e: any) {
    flash.err(e?.message || '删除失败')
  } finally {
    busy.value = false
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
    <button
      type="button"
      class="mb-3 inline-flex items-center gap-1.5 rounded-control border border-line bg-white px-3 py-1.5 text-sm text-muted hover:bg-stone-50"
      @click="router.push({ name: 'customers' })"
    >
      <UiIcon :icon="ArrowLeft" :size="16" />
      返回客户列表
    </button>

    <p v-if="loading" class="text-sm text-muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" hint="无权限或不在数据范围内。" />

    <template v-else-if="detail">
      <header
        class="mb-3 flex flex-wrap items-start justify-between gap-3 rounded-panel border border-line bg-white p-5 shadow-soft"
      >
        <div>
          <h2 class="font-display text-lg font-semibold">
            {{ detail.customer.parent_name }}
            <span class="font-normal text-muted">/</span>
            {{ detail.customer.student_name || '—' }}
          </h2>
          <p class="mt-1.5 text-sm text-muted">
            {{ detail.customer.grade || '年级未知' }}
            · {{ detail.customer.school || '学校未知' }}
            · 负责人 {{ detail.customer.owner_name || '—' }}
          </p>
          <FlashBanner class="mt-2" :message="flash.state.message" :kind="flash.state.kind" />
        </div>
        <div v-if="writable" class="flex flex-wrap gap-2">
          <button
            v-if="!editing"
            type="button"
            :disabled="busy"
            class="rounded-control border border-line bg-white px-3 py-1.5 text-sm text-ink hover:bg-stone-50 disabled:opacity-50"
            @click="editing = true"
          >
            编辑资料
          </button>
          <button
            v-else
            type="button"
            :disabled="busy"
            class="inline-flex items-center gap-1.5 rounded-control border border-line bg-white px-3 py-1.5 text-sm text-ink hover:bg-stone-50 disabled:opacity-50"
            @click="cancelEdit"
          >
            <UiIcon :icon="X" :size="14" />
            取消编辑
          </button>
          <button
            type="button"
            :disabled="busy"
            class="inline-flex items-center gap-1.5 rounded-control border border-line bg-white px-3 py-1.5 text-sm text-danger hover:bg-stone-50 disabled:opacity-50"
            @click="removeCustomer"
          >
            <UiIcon :icon="Trash2" :size="14" />
            {{ busy ? '删除中…' : '删除客户' }}
          </button>
        </div>
      </header>

      <form
        v-if="editing && writable"
        class="mb-3 grid max-w-lg gap-3 rounded-panel border border-line bg-stone-50 p-4"
        @submit.prevent="saveCustomer"
      >
        <strong class="text-sm">编辑客户资料</strong>
        <label class="grid gap-1 text-sm text-muted">
          家长
          <input v-model="editForm.parent_name" required class="rounded-control border border-line px-2.5 py-1.5 text-ink" />
        </label>
        <label class="grid gap-1 text-sm text-muted">
          学员
          <input v-model="editForm.student_name" class="rounded-control border border-line px-2.5 py-1.5 text-ink" />
        </label>
        <label class="grid gap-1 text-sm text-muted">
          年级
          <input v-model="editForm.grade" class="rounded-control border border-line px-2.5 py-1.5 text-ink" />
        </label>
        <label class="grid gap-1 text-sm text-muted">
          学校
          <input v-model="editForm.school" class="rounded-control border border-line px-2.5 py-1.5 text-ink" />
        </label>
        <label class="grid gap-1 text-sm text-muted">
          学段
          <select v-model="editForm.stage" class="rounded-control border border-line px-2.5 py-1.5 text-ink">
            <option value="">—</option>
            <option value="primary">小学</option>
            <option value="junior">初中</option>
            <option value="senior">高中</option>
          </select>
        </label>
        <label v-if="role !== 'advisor'" class="grid gap-1 text-sm text-muted">
          负责人
          <select v-model="editForm.owner_user_id" class="rounded-control border border-line px-2.5 py-1.5 text-ink">
            <option value="">—</option>
            <option v-for="u in users" :key="u.id" :value="u.id">{{ u.name }}</option>
          </select>
        </label>
        <label v-if="role === 'admin'" class="grid gap-1 text-sm text-muted">
          组织
          <select v-model="editForm.org_id" class="rounded-control border border-line px-2.5 py-1.5 text-ink">
            <option value="">—</option>
            <option v-for="o in orgs" :key="o.id" :value="o.id">{{ o.name }}</option>
          </select>
        </label>
        <label class="grid gap-1 text-sm text-muted">
          备注
          <textarea
            v-model="editForm.remark"
            rows="2"
            class="rounded-control border border-line px-2.5 py-1.5 text-ink"
          />
        </label>
        <button
          type="submit"
          :disabled="busy"
          class="inline-flex w-fit items-center gap-1.5 rounded-control bg-fjord px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          <UiIcon :icon="Save" :size="14" />
          {{ busy ? '保存中…' : '保存资料' }}
        </button>
      </form>

      <div class="grid items-start gap-3 lg:grid-cols-[0.9fr_1.1fr]">
        <aside class="rounded-panel border border-line border-l-4 border-l-fjord bg-white p-5 shadow-soft">
          <h3 class="mb-3 font-display text-base font-semibold">画像</h3>
          <p class="mb-2 text-xs font-semibold text-muted">已确认</p>
          <div v-if="confirmedBlocks.length">
            <div v-for="b in confirmedBlocks" :key="'c-' + b.key" class="mb-2.5">
              <strong class="text-sm">{{ b.title }}</strong>
              <div v-for="row in b.rows" :key="row.k" class="mt-0.5 flex gap-2 text-sm">
                <span class="min-w-16 shrink-0 text-muted">{{ row.k }}</span>
                <span class="break-words">{{ row.v }}</span>
              </div>
            </div>
          </div>
          <EmptyState v-else title="尚无已确认画像" hint="顾问在侧栏确认后会出现在这里。" />

          <p class="mb-2 mt-4 text-xs font-semibold text-muted">草稿</p>
          <div v-if="draftBlocks.length">
            <div
              v-for="b in draftBlocks"
              :key="'d-' + b.key"
              class="mb-2.5 rounded-panel bg-fjord-soft/50 p-2"
            >
              <strong class="text-sm">{{ b.title }}</strong>
              <div v-for="row in b.rows" :key="row.k" class="mt-0.5 flex gap-2 text-sm">
                <span class="min-w-16 shrink-0 text-muted">{{ row.k }}</span>
                <span class="break-words">{{ row.v }}</span>
              </div>
            </div>
          </div>
          <EmptyState v-else title="无进行中草稿" />
        </aside>

        <section class="rounded-panel border border-line bg-white p-5 shadow-soft">
          <h3 class="mb-3 font-display text-base font-semibold">沟通与经营</h3>

          <p class="mb-2 text-xs font-semibold text-muted">客服摘要</p>
          <template v-if="writable">
            <textarea
              v-model="csText"
              rows="4"
              placeholder="填写售后/跟进摘要…"
              class="w-full rounded-control border border-line px-2.5 py-1.5 text-ink"
            />
            <button
              type="button"
              :disabled="busy"
              class="mt-2 inline-flex items-center gap-1.5 rounded-control bg-fjord px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
              @click="saveCsSummary"
            >
              <UiIcon :icon="Save" :size="14" />
              {{ busy ? '保存中…' : '保存摘要' }}
            </button>
          </template>
          <p v-else-if="detail.cs_summary?.summary_text" class="whitespace-pre-wrap text-sm leading-relaxed">
            {{ detail.cs_summary.summary_text }}
          </p>
          <EmptyState v-else title="暂无客服摘要" />

          <p class="mb-2 mt-4 text-xs font-semibold text-muted">标签</p>
          <div v-if="(detail.tags || []).length" class="flex flex-wrap gap-1.5">
            <span
              v-for="t in detail.tags"
              :key="t.customer_tag_id || t.id"
              class="rounded-control bg-fjord-soft px-2 py-0.5 text-xs text-fjord"
            >
              {{ t.name }}
            </span>
          </div>
          <EmptyState v-else title="暂无标签" hint="标签挂载请在侧栏操作。" />

          <p class="mb-2 mt-4 text-xs font-semibold text-muted">订单</p>
          <div v-if="(detail.orders || []).length" class="overflow-x-auto">
            <table class="w-full text-left text-sm">
              <thead class="border-b border-line text-muted">
                <tr>
                  <th class="pb-2 pr-3 font-medium">单号</th>
                  <th class="pb-2 pr-3 font-medium">课程</th>
                  <th class="pb-2 pr-3 font-medium">金额</th>
                  <th class="pb-2 font-medium">状态</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="o in detail.orders"
                  :key="o.id"
                  class="border-b border-line/60 hover:bg-fjord-soft/40"
                >
                  <td class="py-2 pr-3">{{ o.external_order_no || o.id }}</td>
                  <td class="py-2 pr-3">{{ o.title }}</td>
                  <td class="py-2 pr-3">{{ o.amount ?? '—' }}</td>
                  <td class="py-2">{{ o.status }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <EmptyState v-else title="暂无订单" hint="可在「订单」页新建。" />

          <p class="mb-2 mt-4 text-xs font-semibold text-muted">沟通时间线（近 30 条）</p>
          <ul v-if="messages.length" class="max-h-[420px] list-none overflow-auto p-0">
            <li
              v-for="m in messages"
              :key="m.id"
              class="grid gap-0.5 border-b border-line/60 py-2 text-sm"
            >
              <span
                class="text-[11px]"
                :class="m.direction === 'out' ? 'text-fjord' : 'text-muted'"
              >
                {{ m.direction === 'out' ? '顾问' : '家长' }}
              </span>
              <span>{{ m.content || '—' }}</span>
              <span v-if="m.msg_time" class="text-[11px] text-muted">
                {{ m.msg_time.replace('T', ' ').replace('Z', '') }}
              </span>
            </li>
          </ul>
          <EmptyState v-else title="暂无沟通记录" />
        </section>
      </div>
    </template>
  </div>
</template>
