<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import EmptyState from '../components/EmptyState.vue'
import PaginationBar from '../components/PaginationBar.vue'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { api } = useAuth()
const customers = ref<any>(null)
const error = ref('')
const loading = ref(true)
const keyword = ref('')
const grade = ref('')
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
    if (keyword.value.trim()) qs.set('keyword', keyword.value.trim())
    if (grade.value.trim()) qs.set('grade', grade.value.trim())
    customers.value = await api(`/admin/customers?${qs}`)
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function openCustomer(id: number) {
  void router.push({ name: 'customer-detail', params: { id: String(id) } })
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
      <h2>客户</h2>
      <form class="search" @submit.prevent="onSearch">
        <input v-model="keyword" placeholder="搜索家长/学员…" />
        <input v-model="grade" placeholder="年级筛选…" />
        <button type="submit" class="primary">筛选</button>
      </form>
    </div>
    <p v-if="loading" class="muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <EmptyState
      v-else-if="!(customers?.items || []).length"
      title="暂无客户"
      hint="数据范围外为空，或尚未 seed。"
    />
    <template v-else>
      <table class="data">
        <thead>
          <tr>
            <th>家长/学员</th>
            <th>年级</th>
            <th>标签</th>
            <th>负责人</th>
            <th>画像</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="c in customers.items"
            :key="c.id"
            class="clickable"
            @click="openCustomer(c.id)"
          >
            <td>{{ c.parent_name }} / {{ c.student_name || '—' }}</td>
            <td>{{ c.grade || '—' }}</td>
            <td>{{ (c.tags || []).join('、') || '—' }}</td>
            <td>{{ c.owner_name || '—' }}</td>
            <td>{{ c.profile_status || '—' }}</td>
          </tr>
        </tbody>
      </table>
      <PaginationBar
        :page="page"
        :page-size="pageSize"
        :total="customers.total || 0"
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
  flex-wrap: wrap;
}
.search input {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 10px;
  min-width: 120px;
}
</style>
