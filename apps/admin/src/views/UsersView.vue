<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import EmptyState from '../components/EmptyState.vue'
import PaginationBar from '../components/PaginationBar.vue'
import { roleLabel, useAuth } from '../composables/useAuth'
import { canCreateAccount, canWriteUsers } from '../nav'

const { api, role, me } = useAuth()
const users = ref<any>(null)
const orgs = ref<any[]>([])
const error = ref('')
const loading = ref(true)
const flash = ref('')
const page = ref(1)
const pageSize = 20
const keyword = ref('')
const filterRole = ref('')
const filterOrg = ref('' as string | number | '')

const writable = computed(() => canWriteUsers(role.value))
const canAccount = computed(() => canCreateAccount(role.value))

const createForm = ref({
  name: '',
  role: 'advisor',
  org_id: '' as string | number | '',
  mobile: '',
})
const editingId = ref<number | null>(null)
const editForm = ref({
  name: '',
  role: 'advisor',
  org_id: '' as string | number | '',
  status: 1,
  mobile: '',
})
const accountUserId = ref<number | null>(null)
const accountForm = ref({ login_name: '', password: '' })

function orgName(id?: number | null) {
  if (id == null) return '—'
  return orgs.value.find((o) => o.id === id)?.name || `#${id}`
}

const roleOptions = computed(() => {
  if (role.value === 'regional') {
    return [
      { value: 'regional', label: '区域主管' },
      { value: 'advisor', label: '顾问' },
    ]
  }
  return [
    { value: 'admin', label: '管理员' },
    { value: 'regional', label: '区域主管' },
    { value: 'advisor', label: '顾问' },
  ]
})

async function loadOrgs() {
  try {
    const data = await api('/admin/orgs')
    orgs.value = data?.items || []
  } catch {
    orgs.value = []
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
    if (filterRole.value) qs.set('role', filterRole.value)
    if (filterOrg.value !== '') qs.set('org_id', String(filterOrg.value))
    users.value = await api(`/admin/users?${qs}`)
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function createUser() {
  if (!createForm.value.name.trim()) return
  try {
    await api('/admin/users', {
      method: 'POST',
      body: JSON.stringify({
        name: createForm.value.name.trim(),
        role: createForm.value.role,
        org_id: createForm.value.org_id === '' ? null : Number(createForm.value.org_id),
        mobile: createForm.value.mobile.trim() || null,
      }),
    })
    createForm.value = { name: '', role: 'advisor', org_id: me.value?.org_id ?? '', mobile: '' }
    flash.value = '员工已创建'
    await load()
  } catch (e: any) {
    flash.value = e?.message || '创建失败'
  }
}

function startEdit(u: any) {
  editingId.value = u.id
  editForm.value = {
    name: u.name || '',
    role: u.role || 'advisor',
    org_id: u.org_id ?? '',
    status: u.status ?? 1,
    mobile: u.mobile || '',
  }
}

async function saveEdit() {
  if (editingId.value == null) return
  try {
    await api(`/admin/users/${editingId.value}`, {
      method: 'PATCH',
      body: JSON.stringify({
        name: editForm.value.name.trim(),
        role: editForm.value.role,
        org_id: editForm.value.org_id === '' ? null : Number(editForm.value.org_id),
        status: Number(editForm.value.status),
        mobile: editForm.value.mobile.trim() || null,
      }),
    })
    editingId.value = null
    flash.value = '员工已更新'
    await load()
  } catch (e: any) {
    flash.value = e?.message || '更新失败'
  }
}

function openAccount(userId: number) {
  accountUserId.value = userId
  accountForm.value = { login_name: '', password: '' }
}

async function createAccount() {
  if (accountUserId.value == null) return
  try {
    await api(`/admin/users/${accountUserId.value}/account`, {
      method: 'POST',
      body: JSON.stringify(accountForm.value),
    })
    flash.value = `已开通账号 ${accountForm.value.login_name}`
    accountUserId.value = null
  } catch (e: any) {
    flash.value = e?.message || '开账号失败'
  }
}

async function removeUser(id: number) {
  if (!window.confirm('软删除该员工？删除后将无法登录且不在列表显示。')) return
  try {
    await api(`/admin/users/${id}`, { method: 'DELETE' })
    flash.value = '员工已删除'
    editingId.value = null
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
  await loadOrgs()
  await load()
})
</script>

<template>
  <section class="card">
    <h2>员工</h2>
    <p v-if="flash" class="muted">{{ flash }}</p>

    <form class="filters" @submit.prevent="onSearch">
      <input v-model="keyword" placeholder="姓名/手机…" />
      <select v-model="filterRole">
        <option value="">全部角色</option>
        <option value="admin">管理员</option>
        <option value="regional">区域主管</option>
        <option value="advisor">顾问</option>
      </select>
      <select v-model="filterOrg">
        <option value="">全部组织</option>
        <option v-for="o in orgs" :key="o.id" :value="o.id">{{ o.name }}</option>
      </select>
      <button type="submit" class="primary">筛选</button>
    </form>

    <form v-if="writable" class="form" @submit.prevent="createUser">
      <strong>新建员工</strong>
      <label>姓名 <input v-model="createForm.name" required /></label>
      <label>
        角色
        <select v-model="createForm.role">
          <option v-for="r in roleOptions" :key="r.value" :value="r.value">{{ r.label }}</option>
        </select>
      </label>
      <label>
        组织
        <select v-model="createForm.org_id">
          <option value="">默认</option>
          <option v-for="o in orgs" :key="o.id" :value="o.id">{{ o.name }}</option>
        </select>
      </label>
      <label>手机 <input v-model="createForm.mobile" /></label>
      <button type="submit" class="primary">创建</button>
    </form>

    <p v-if="loading" class="muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <EmptyState v-else-if="!(users?.items || []).length" title="暂无员工" />
    <template v-else>
      <table class="data">
        <thead>
          <tr><th>姓名</th><th>角色</th><th>组织</th><th>手机</th><th>状态</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="u in users.items" :key="u.id">
            <td>
              <input v-if="editingId === u.id" v-model="editForm.name" />
              <template v-else>{{ u.name }}</template>
            </td>
            <td>
              <select v-if="editingId === u.id" v-model="editForm.role">
                <option v-for="r in roleOptions" :key="r.value" :value="r.value">{{ r.label }}</option>
              </select>
              <template v-else>{{ roleLabel(u.role) }}</template>
            </td>
            <td>
              <select v-if="editingId === u.id" v-model="editForm.org_id">
                <option value="">—</option>
                <option v-for="o in orgs" :key="o.id" :value="o.id">{{ o.name }}</option>
              </select>
              <template v-else>{{ orgName(u.org_id) }}</template>
            </td>
            <td>
              <input v-if="editingId === u.id" v-model="editForm.mobile" />
              <template v-else>{{ u.mobile || '—' }}</template>
            </td>
            <td>
              <select v-if="editingId === u.id" v-model.number="editForm.status">
                <option :value="1">启用</option>
                <option :value="0">停用</option>
              </select>
              <template v-else>{{ u.status === 1 ? '启用' : '停用' }}</template>
            </td>
            <td class="actions">
              <template v-if="writable && editingId === u.id">
                <button type="button" class="primary" @click="saveEdit">保存</button>
                <button type="button" @click="editingId = null">取消</button>
              </template>
              <template v-else>
                <button v-if="writable" type="button" @click="startEdit(u)">改</button>
                <button v-if="canAccount" type="button" @click="openAccount(u.id)">开账号</button>
                <button v-if="writable" type="button" @click="removeUser(u.id)">删</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
      <PaginationBar
        :page="page"
        :page-size="pageSize"
        :total="users.total || 0"
        @update:page="(n) => (page = n)"
      />
    </template>

    <div v-if="accountUserId != null" class="account card-inner">
      <strong>开通后台账号 · 用户 #{{ accountUserId }}</strong>
      <label>登录名 <input v-model="accountForm.login_name" /></label>
      <label>密码 <input v-model="accountForm.password" type="password" /></label>
      <div class="actions">
        <button type="button" class="primary" @click="createAccount">开通</button>
        <button type="button" @click="accountUserId = null">取消</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 10px; font-size: 1.05rem; }
.filters {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.filters input,
.filters select,
.form input,
.form select,
.account input,
td input,
td select {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 8px;
  color: var(--ink);
}
.form, .account {
  display: grid;
  gap: 8px;
  max-width: 480px;
  margin-bottom: 14px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fafbfc;
}
.form label, .account label {
  display: grid;
  gap: 4px;
  font-size: 13px;
  color: var(--muted);
}
.actions { display: flex; gap: 6px; flex-wrap: wrap; }
.card-inner { margin-top: 12px; }
</style>
