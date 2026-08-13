<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import EmptyState from '../components/EmptyState.vue'
import PaginationBar from '../components/PaginationBar.vue'
import { useAuth } from '../composables/useAuth'

const { api } = useAuth()
const orders = ref<any>(null)
const error = ref('')
const loading = ref(true)
const status = ref('')
const page = ref(1)
const pageSize = 20

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

function onSearch() {
  page.value = 1
  void load()
}

watch(page, () => {
  void load()
})

onMounted(() => {
  void load()
})
</script>

<template>
  <section class="card">
    <div class="head">
      <h2>订单</h2>
      <form class="search" @submit.prevent="onSearch">
        <select v-model="status">
          <option value="">全部状态</option>
          <option value="paid">paid</option>
          <option value="unpaid">unpaid</option>
          <option value="refunded">refunded</option>
          <option value="cancelled">cancelled</option>
        </select>
        <button type="submit" class="primary">筛选</button>
      </form>
    </div>
    <p v-if="loading" class="muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <EmptyState v-else-if="!(orders?.items || []).length" title="暂无订单" />
    <template v-else>
      <table class="data">
        <thead>
          <tr><th>单号</th><th>客户</th><th>课程</th><th>金额</th><th>状态</th></tr>
        </thead>
        <tbody>
          <tr v-for="o in orders.items" :key="o.id">
            <td>{{ o.external_order_no }}</td>
            <td>{{ o.parent_name }}</td>
            <td>{{ o.title }}</td>
            <td>{{ o.amount }}</td>
            <td>{{ o.status }}</td>
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
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
h2 { margin: 0; font-size: 1.05rem; }
.search {
  display: flex;
  gap: 6px;
}
.search select {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 10px;
}
</style>
