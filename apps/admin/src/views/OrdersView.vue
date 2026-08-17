<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { Pencil, Plus, Save, Trash2, X } from '@lucide/vue'
import EmptyState from '../components/EmptyState.vue'
import FlashBanner from '../components/FlashBanner.vue'
import PaginationBar from '../components/PaginationBar.vue'
import UiIcon from '../components/UiIcon.vue'
import { useFlash } from '../composables/useFlash'
import { useAuth } from '../composables/useAuth'
import { canWriteOrders } from '../nav'

const { api, role } = useAuth()
const flash = useFlash()
const orders = ref<any>(null)
const customers = ref<any[]>([])
const error = ref('')
const loading = ref(true)
const busy = ref(false)
const status = ref('')
const page = ref(1)
const pageSize = 20
const writable = canWriteOrders(role.value)
const showCreate = ref(false)
const customerKeyword = ref('')

const form = ref({
  customer_id: '' as string | number | '',
  external_order_no: '',
  title: '',
  amount: 0,
  status: 'paid',
})
const editingId = ref<number | null>(null)
const editForm = ref({
  title: '',
  amount: 0,
  status: 'paid',
  external_order_no: '',
})

const statusOptions = [
  { value: 'paid', label: '已支付' },
  { value: 'unpaid', label: '未支付' },
  { value: 'refunded', label: '已退款' },
  { value: 'cancelled', label: '已取消' },
]

function statusLabel(s?: string) {
  return statusOptions.find((x) => x.value === s)?.label || s || '—'
}

function formatDateTime(iso?: string | null) {
  if (!iso) return '—'
  return iso.replace('T', ' ').replace('Z', '').slice(0, 16)
}

async function loadCustomers() {
  busy.value = true
  try {
    const qs = new URLSearchParams({ page: '1', page_size: '50' })
    if (customerKeyword.value.trim()) qs.set('keyword', customerKeyword.value.trim())
    const data = await api(`/admin/customers?${qs}`)
    customers.value = data?.items || []
  } catch {
    customers.value = []
  } finally {
    busy.value = false
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const qs = new URLSearchParams({
      page: String(page.value),
      page_size: String(pageSize),
    })
    if (status.value) qs.set('status', status.value)
    orders.value = await api(`/admin/orders?${qs}`)
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function createOrder() {
  if (form.value.customer_id === '') {
    flash.err('请选择客户')
    return
  }
  if (!form.value.title.trim()) {
    flash.err('请填写课程/标题')
    return
  }
  busy.value = true
  try {
    await api('/admin/orders', {
      method: 'POST',
      body: JSON.stringify({
        customer_id: Number(form.value.customer_id),
        external_order_no: form.value.external_order_no.trim() || null,
        title: form.value.title.trim(),
        amount: Number(form.value.amount) || 0,
        status: form.value.status,
      }),
    })
    flash.ok('订单已创建')
    showCreate.value = false
    form.value = {
      customer_id: '',
      external_order_no: '',
      title: '',
      amount: 0,
      status: 'paid',
    }
    await load()
  } catch (e: any) {
    flash.err(e?.message || '创建失败')
  } finally {
    busy.value = false
  }
}

function startEdit(o: any) {
  editingId.value = o.id
  editForm.value = {
    title: o.title || '',
    amount: o.amount ?? 0,
    status: o.status || 'paid',
    external_order_no: o.external_order_no || '',
  }
}

async function saveEdit() {
  if (editingId.value == null) return
  if (!editForm.value.title.trim()) {
    flash.err('请填写课程/标题')
    return
  }
  busy.value = true
  try {
    await api(`/admin/orders/${editingId.value}`, {
      method: 'PATCH',
      body: JSON.stringify({
        title: editForm.value.title.trim(),
        amount: Number(editForm.value.amount) || 0,
        status: editForm.value.status,
        external_order_no: editForm.value.external_order_no.trim() || null,
      }),
    })
    editingId.value = null
    flash.ok('订单已更新')
    await load()
  } catch (e: any) {
    flash.err(e?.message || '更新失败')
  } finally {
    busy.value = false
  }
}

async function removeOrder(o: any) {
  const label = o.external_order_no || o.title || `#${o.id}`
  if (!window.confirm(`确认删除订单「${label}」？此操作不可恢复。`)) return
  busy.value = true
  try {
    await api(`/admin/orders/${o.id}`, { method: 'DELETE' })
    flash.ok('订单已删除')
    editingId.value = null
    await load()
  } catch (e: any) {
    flash.err(e?.message || '删除失败')
  } finally {
    busy.value = false
  }
}

function onSearch() {
  page.value = 1
  void load()
}

watch(page, () => {
  void load()
})

onMounted(async () => {
  await loadCustomers()
  await load()
})
</script>

<template>
  <section class="rounded-panel border border-line bg-white p-5 shadow-soft">
    <div class="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="font-display text-lg font-semibold">订单</h2>
        <p class="mt-1 text-sm text-muted">按状态筛选；可新建、编辑状态或删除记录。</p>
        <FlashBanner class="mt-2" :message="flash.state.message" :kind="flash.state.kind" />
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <form class="flex flex-wrap items-center gap-2" @submit.prevent="onSearch">
          <select v-model="status" class="rounded-control border border-line px-2.5 py-1.5 text-sm">
            <option value="">全部状态</option>
            <option v-for="s in statusOptions" :key="s.value" :value="s.value">
              {{ s.label }}
            </option>
          </select>
          <button
            type="submit"
            class="rounded-control border border-line bg-white px-3 py-1.5 text-sm text-ink hover:bg-stone-50 disabled:opacity-50"
          >
            筛选
          </button>
        </form>
        <button
          v-if="writable"
          type="button"
          class="inline-flex items-center gap-1.5 rounded-control bg-fjord px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
          @click="showCreate = !showCreate"
        >
          <UiIcon :icon="showCreate ? X : Plus" :size="14" />
          {{ showCreate ? '收起' : '新建订单' }}
        </button>
      </div>
    </div>

    <form
      v-if="showCreate && writable"
      class="mb-4 grid max-w-md gap-3 rounded-panel border border-line bg-stone-50 p-4"
      @submit.prevent="createOrder"
    >
      <strong class="text-sm">新建订单</strong>
      <label class="grid gap-1 text-sm text-muted">
        搜索客户
        <div class="flex gap-2">
          <input
            v-model="customerKeyword"
            placeholder="家长/学员关键词…"
            class="min-w-0 flex-1 rounded-control border border-line px-2.5 py-1.5 text-ink"
          />
          <button
            type="button"
            :disabled="busy"
            class="shrink-0 rounded-control border border-line bg-white px-3 py-1.5 text-sm text-ink hover:bg-stone-50 disabled:opacity-50"
            @click="loadCustomers"
          >
            搜索
          </button>
        </div>
      </label>
      <label class="grid gap-1 text-sm text-muted">
        客户
        <select
          v-model="form.customer_id"
          required
          class="rounded-control border border-line px-2.5 py-1.5 text-ink"
        >
          <option disabled value="">请选择</option>
          <option v-for="c in customers" :key="c.id" :value="c.id">
            #{{ c.id }} {{ c.parent_name }}/{{ c.student_name || '—' }}
          </option>
        </select>
      </label>
      <label class="grid gap-1 text-sm text-muted">
        课程/标题
        <input v-model="form.title" required class="rounded-control border border-line px-2.5 py-1.5 text-ink" />
      </label>
      <label class="grid gap-1 text-sm text-muted">
        金额
        <input
          v-model.number="form.amount"
          type="number"
          min="0"
          step="0.01"
          class="rounded-control border border-line px-2.5 py-1.5 text-ink"
        />
      </label>
      <label class="grid gap-1 text-sm text-muted">
        外部单号
        <input
          v-model="form.external_order_no"
          placeholder="可选"
          class="rounded-control border border-line px-2.5 py-1.5 text-ink"
        />
      </label>
      <label class="grid gap-1 text-sm text-muted">
        状态
        <select v-model="form.status" class="rounded-control border border-line px-2.5 py-1.5 text-ink">
          <option v-for="s in statusOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
      </label>
      <button
        type="submit"
        :disabled="busy"
        class="inline-flex w-fit items-center gap-1.5 rounded-control bg-fjord px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
      >
        <UiIcon :icon="Plus" :size="14" />
        {{ busy ? '创建中…' : '创建' }}
      </button>
    </form>

    <p v-if="loading" class="text-sm text-muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <EmptyState
      v-else-if="!(orders?.items || []).length"
      title="暂无订单"
      hint="可新建订单，或先有客户后再录单。"
    />
    <template v-else>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="border-b border-line text-muted">
            <tr>
              <th class="pb-2 pr-3 font-medium">单号</th>
              <th class="pb-2 pr-3 font-medium">客户</th>
              <th class="pb-2 pr-3 font-medium">课程</th>
              <th class="pb-2 pr-3 font-medium">金额</th>
              <th class="pb-2 pr-3 font-medium">状态</th>
              <th class="pb-2 pr-3 font-medium">支付时间</th>
              <th v-if="writable" class="pb-2 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="o in orders.items"
              :key="o.id"
              class="border-b border-line/60 hover:bg-fjord-soft/40"
            >
              <template v-if="editingId === o.id">
                <td class="py-2 pr-3">
                  <input
                    v-model="editForm.external_order_no"
                    class="w-full rounded-control border border-line px-2 py-1 text-sm"
                  />
                </td>
                <td class="py-2 pr-3">
                  <RouterLink
                    v-if="o.customer_id"
                    :to="`/customers/${o.customer_id}`"
                    class="text-fjord hover:underline"
                  >
                    {{ o.parent_name }}
                  </RouterLink>
                  <span v-else>{{ o.parent_name }}</span>
                </td>
                <td class="py-2 pr-3">
                  <input v-model="editForm.title" class="w-full rounded-control border border-line px-2 py-1 text-sm" />
                </td>
                <td class="py-2 pr-3">
                  <input
                    v-model.number="editForm.amount"
                    type="number"
                    step="0.01"
                    class="w-full rounded-control border border-line px-2 py-1 text-sm"
                  />
                </td>
                <td class="py-2 pr-3">
                  <select v-model="editForm.status" class="rounded-control border border-line px-2 py-1 text-sm">
                    <option v-for="s in statusOptions" :key="s.value" :value="s.value">
                      {{ s.label }}
                    </option>
                  </select>
                </td>
                <td class="py-2 pr-3 text-muted">{{ formatDateTime(o.paid_at) }}</td>
                <td class="py-2">
                  <div class="flex flex-wrap justify-end gap-1.5">
                    <button
                      type="button"
                      :disabled="busy"
                      class="inline-flex items-center gap-1 rounded-control bg-fjord px-2.5 py-1 text-xs font-semibold text-white disabled:opacity-50"
                      @click="saveEdit"
                    >
                      <UiIcon :icon="Save" :size="14" />
                      {{ busy ? '保存中…' : '保存' }}
                    </button>
                    <button
                      type="button"
                      :disabled="busy"
                      class="inline-flex items-center gap-1 rounded-control border border-line bg-white px-2.5 py-1 text-xs text-ink hover:bg-stone-50 disabled:opacity-50"
                      @click="editingId = null"
                    >
                      <UiIcon :icon="X" :size="14" />
                      取消
                    </button>
                  </div>
                </td>
              </template>
              <template v-else>
                <td class="py-2 pr-3">{{ o.external_order_no || o.id }}</td>
                <td class="py-2 pr-3">
                  <RouterLink
                    v-if="o.customer_id"
                    :to="`/customers/${o.customer_id}`"
                    class="text-fjord hover:underline"
                  >
                    {{ o.parent_name }}
                  </RouterLink>
                  <span v-else>{{ o.parent_name }}</span>
                </td>
                <td class="py-2 pr-3">{{ o.title }}</td>
                <td class="py-2 pr-3">{{ o.amount }}</td>
                <td class="py-2 pr-3">{{ statusLabel(o.status) }}</td>
                <td class="py-2 pr-3 text-muted">{{ formatDateTime(o.paid_at) }}</td>
                <td v-if="writable" class="py-2">
                  <div class="flex flex-wrap justify-end gap-1.5">
                    <button
                      type="button"
                      :disabled="busy"
                      class="inline-flex items-center gap-1 rounded-control border border-line bg-white px-2.5 py-1 text-xs text-ink hover:bg-stone-50 disabled:opacity-50"
                      :aria-label="`编辑订单 ${o.external_order_no || o.title || o.id}`"
                      @click="startEdit(o)"
                    >
                      <UiIcon :icon="Pencil" :size="14" />
                      编辑
                    </button>
                    <button
                      type="button"
                      :disabled="busy"
                      class="inline-flex items-center gap-1 rounded-control border border-line bg-white px-2.5 py-1 text-xs text-danger hover:bg-stone-50 disabled:opacity-50"
                      :aria-label="`删除订单 ${o.external_order_no || o.title || o.id}`"
                      @click="removeOrder(o)"
                    >
                      <UiIcon :icon="Trash2" :size="14" />
                      删除
                    </button>
                  </div>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
      <PaginationBar
        :page="page"
        :page-size="pageSize"
        :total="orders.total || 0"
        @update:page="(n) => (page = n)"
      />
    </template>
  </section>
</template>
