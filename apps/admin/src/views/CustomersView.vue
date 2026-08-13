<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import EmptyState from '../components/EmptyState.vue'
import PaginationBar from '../components/PaginationBar.vue'
import { useAuth } from '../composables/useAuth'
import { canWriteCustomers } from '../nav'

const router = useRouter()
const { api, role, me } = useAuth()
const customers = ref<any>(null)
const users = ref<any[]>([])
const error = ref('')
const flash = ref('')
const loading = ref(true)
const keyword = ref('')
const grade = ref('')
const page = ref(1)
const pageSize = 20
const showCreate = ref(false)
const writable = canWriteCustomers(role.value)

const form = ref({
  parent_name: '',
  student_name: '',
  grade: '',
  school: '',
  stage: 'junior',
  owner_user_id: '' as string | number | '',
  remark: '',
})

async function loadUsers() {
  if (role.value === 'advisor') return
  try {
    const data = await api('/admin/users?page=1&page_size=100&role=advisor')
    users.value = data?.items || []
  } catch {
    users.value = []
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
    if (keyword.value.trim()) qs.set('keyword', keyword.value.trim())
    if (grade.value.trim()) qs.set('grade', grade.value.trim())
    customers.value = await api(`/admin/customers?${qs}`)
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function createCustomer() {
  if (!form.value.parent_name.trim()) return
  try {
    const body: Record<string, unknown> = {
      parent_name: form.value.parent_name.trim(),
      student_name: form.value.student_name.trim() || null,
      grade: form.value.grade.trim() || null,
      school: form.value.school.trim() || null,
      stage: form.value.stage || null,
      remark: form.value.remark.trim() || null,
    }
    if (form.value.owner_user_id !== '') {
      body.owner_user_id = Number(form.value.owner_user_id)
    }
    const data = await api('/admin/customers', {
      method: 'POST',
      body: JSON.stringify(body),
    })
    flash.value = '客户已创建'
    showCreate.value = false
    form.value = {
      parent_name: '',
      student_name: '',
      grade: '',
      school: '',
      stage: 'junior',
      owner_user_id: me.value?.id ?? '',
      remark: '',
    }
    await load()
    if (data?.id) openCustomer(data.id)
  } catch (e: any) {
    flash.value = e?.message || '创建失败'
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

onMounted(async () => {
  form.value.owner_user_id = me.value?.id ?? ''
  await loadUsers()
  await load()
})
</script>

<template>
  <section class="card">
    <div class="head">
      <h2>客户</h2>
      <div class="actions">
        <form class="search" @submit.prevent="onSearch">
          <input v-model="keyword" placeholder="搜索家长/学员…" />
          <input v-model="grade" placeholder="年级筛选…" />
          <button type="submit" class="primary">筛选</button>
        </form>
        <button v-if="writable" type="button" class="primary" @click="showCreate = !showCreate">
          {{ showCreate ? '收起' : '新建客户' }}
        </button>
      </div>
    </div>
    <p v-if="flash" class="muted">{{ flash }}</p>

    <form v-if="showCreate && writable" class="form" @submit.prevent="createCustomer">
      <strong>新建客户</strong>
      <label>家长姓名 <input v-model="form.parent_name" required /></label>
      <label>学员姓名 <input v-model="form.student_name" /></label>
      <label>年级 <input v-model="form.grade" placeholder="如 初二" /></label>
      <label>学校 <input v-model="form.school" /></label>
      <label>
        学段
        <select v-model="form.stage">
          <option value="primary">小学</option>
          <option value="junior">初中</option>
          <option value="senior">高中</option>
        </select>
      </label>
      <label v-if="role !== 'advisor'">
        负责顾问
        <select v-model="form.owner_user_id">
          <option value="">默认自己</option>
          <option v-for="u in users" :key="u.id" :value="u.id">{{ u.name }}</option>
        </select>
      </label>
      <label>备注 <input v-model="form.remark" /></label>
      <button type="submit" class="primary">创建</button>
    </form>

    <p v-if="loading" class="muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <EmptyState
      v-else-if="!(customers?.items || []).length"
      title="暂无客户"
      hint="可点「新建客户」，或先 seed 演示数据。"
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
  flex-wrap: wrap;
}
.search input,
.form input,
.form select {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 10px;
  min-width: 120px;
  color: var(--ink);
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
.muted { color: var(--muted); }
</style>
