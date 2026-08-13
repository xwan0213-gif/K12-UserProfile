<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import EmptyState from '../components/EmptyState.vue'
import PaginationBar from '../components/PaginationBar.vue'
import { useAuth } from '../composables/useAuth'
import { canWriteOrders } from '../nav'

const { api, role } = useAuth()
const orders = ref<any>(null)
const customers = ref<any[]>([])
const error = ref('')
const flash = ref('')
const loading = ref(true)
const status = ref('')
const page = ref(1)
const pageSize = 20
const writable = canWriteOrders(role.value)
const showCreate = ref(false)

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

async function loadCustomers() {
  try {
    const data = await api('/admin/customers?page=1&page_size=100')
    customers.value = data?.items || []
  } catch {
    customers.value = []
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
  if (form.value.customer_id === '' || !form.value.title.trim()) return
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
    flash.value = '订单已创建'
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
    flash.value = e?.message || '创建失败'
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
    flash.value = '订单已更新'
    await load()
  } catch (e: any) {
    flash.value = e?.message || '更新失败'
  }
}

async function removeOrder(id: number) {
  if (!window.confirm('确认删除该订单记录？')) return
  try {
    await api(`/admin/orders/${id}`, { method: 'DELETE' })
    flash.value = '订单已删除'
    await load()
  } catch (e: any) {
    flash.value = e?.message || '删除失败'
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
  <section class="card">
    <div class="head">
      <h2>订单</h2>
      <div class="actions">
        <form class="search" @submit.prevent="onSearch">
          <select v-model="status">
            <option value="">全部状态</option>
            <option v-for="s in statusOptions" :key="s.value" :value="s.value">
              {{ s.label }}
            </option>
          </select>
          <button type="submit" class="primary">筛选</button>
        </form>
        <button v-if="writable" type="button" class="primary" @click="showCreate = !showCreate">
          {{ showCreate ? '收起' : '新建订单' }}
        </button>
      </div>
    </div>
    <p v-if="flash" class="muted">{{ flash }}</p>

    <form v-if="showCreate && writable" class="form" @submit.prevent="createOrder">
      <strong>新建订单</strong>
      <label>
        客户
        <select v-model="form.customer_id" required>
          <option disabled value="">请选择</option>
          <option v-for="c in customers" :key="c.id" :value="c.id">
            #{{ c.id }} {{ c.parent_name }}/{{ c.student_name || '—' }}
          </option>
        </select>
      </label>
      <label>课程/标题 <input v-model="form.title" required /></label>
      <label>金额 <input v-model.number="form.amount" type="number" min="0" step="0.01" /></label>
      <label>外部单号 <input v-model="form.external_order_no" placeholder="可选" /></label>
      <label>
        状态
        <select v-model="form.status">
          <option v-for="s in statusOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
      </label>
      <button type="submit" class="primary">创建</button>
    </form>

    <p v-if="loading" class="muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <EmptyState v-else-if="!(orders?.items || []).length" title="暂无订单" hint="可新建订单，或先有客户后再录单。" />
    <template v-else>
      <table class="data">
        <thead>
          <tr>
            <th>单号</th>
            <th>客户</th>
            <th>课程</th>
            <th>金额</th>
            <th>状态</th>
            <th v-if="writable"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="o in orders.items" :key="o.id">
            <template v-if="editingId === o.id">
              <td><input v-model="editForm.external_order_no" /></td>
              <td>{{ o.parent_name }}</td>
              <td><input v-model="editForm.title" /></td>
              <td><input v-model.number="editForm.amount" type="number" step="0.01" /></td>
              <td>
                <select v-model="editForm.status">
                  <option v-for="s in statusOptions" :key="s.value" :value="s.value">
                    {{ s.label }}
                  </option>
                </select>
              </td>
              <td class="row-actions">
                <button type="button" class="primary" @click="saveEdit">保存</button>
                <button type="button" @click="editingId = null">取消</button>
              </td>
            </template>
            <template v-else>
              <td>{{ o.external_order_no || o.id }}</td>
              <td>{{ o.parent_name }}</td>
              <td>{{ o.title }}</td>
              <td>{{ o.amount }}</td>
              <td>{{ statusLabel(o.status) }}</td>
              <td v-if="writable" class="row-actions">
                <button type="button" @click="startEdit(o)">改</button>
                <button type="button" @click="removeOrder(o.id)">删</button>
              </td>
            </template>
          </tr>
        </tbody>
      </table>
      <PaginationBar
        :page="page"
        :page-size="pageSize"
        :total="orders.total || 0"
        @update:page="(n) => (page = n)"
      />
    </template>
  </section>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
h2 { margin: 0; font-size: 1.05rem; }
.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.search {
  display: flex;
  gap: 6px;
}
.search select,
.form input,
.form select,
td input,
td select {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 10px;
  color: var(--ink);
  width: 100%;
}
.form {
  display: grid;
  gap: 8px;
  max-width: 480px;
  margin-bottom: 14px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fafbfc;
}
.form label {
  display: grid;
  gap: 4px;
  font-size: 13px;
  color: var(--muted);
}
.row-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.muted { color: var(--muted); }
</style>
