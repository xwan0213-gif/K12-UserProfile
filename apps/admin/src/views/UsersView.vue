<script setup lang="ts">
import { onMounted, ref } from 'vue'
import EmptyState from '../components/EmptyState.vue'
import { roleLabel, useAuth } from '../composables/useAuth'

const { api } = useAuth()
const users = ref<any>(null)
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    users.value = await api('/admin/users?page=1&page_size=50')
  } catch (e: any) {
    error.value = e?.message || '加载失败（员工列表仅管理员/区域主管可见）'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="card">
    <h2>员工</h2>
    <p v-if="loading" class="muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <EmptyState v-else-if="!(users?.items || []).length" title="暂无员工" />
    <table v-else class="data">
      <thead>
        <tr><th>姓名</th><th>角色</th><th>组织</th><th>状态</th></tr>
      </thead>
      <tbody>
        <tr v-for="u in users.items" :key="u.id">
          <td>{{ u.name }}</td>
          <td>{{ roleLabel(u.role) }}</td>
          <td>{{ u.org_id ?? '—' }}</td>
          <td>{{ u.status }}</td>
        </tr>
      </tbody>
    </table>
    <p class="muted tip">创建/改账号属阶段 D.4，本页先展示范围数据。</p>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 10px; font-size: 1.05rem; }
.tip { margin-top: 10px; }
</style>
