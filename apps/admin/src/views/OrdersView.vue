<script setup lang="ts">
import { onMounted, ref } from 'vue'
import EmptyState from '../components/EmptyState.vue'
import { useAuth } from '../composables/useAuth'

const { api } = useAuth()
const orders = ref<any>(null)
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    orders.value = await api('/admin/orders?page=1&page_size=50')
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="card">
    <h2>订单</h2>
    <p v-if="loading" class="muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <EmptyState v-else-if="!(orders?.items || []).length" title="暂无订单" />
    <table v-else class="data">
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
  </section>
</template>

<style scoped>
h2 { margin: 0 0 10px; font-size: 1.05rem; }
</style>
