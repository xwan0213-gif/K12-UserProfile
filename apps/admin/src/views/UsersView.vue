<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { KeyRound, Pencil, Plus, Save, Trash2, UserPlus, X } from '@lucide/vue'
import EmptyState from '../components/EmptyState.vue'
import FlashBanner from '../components/FlashBanner.vue'
import PaginationBar from '../components/PaginationBar.vue'
import UiIcon from '../components/UiIcon.vue'
import { useFlash } from '../composables/useFlash'
import { roleLabel, useAuth } from '../composables/useAuth'
import { canCreateAccount, canWriteUsers } from '../nav'

const { api, role, me } = useAuth()
const flash = useFlash()
const users = ref<any>(null)
const orgs = ref<any[]>([])
const error = ref('')
const loading = ref(true)
const busy = ref(false)
const page = ref(1)
const pageSize = 20
const keyword = ref('')
const filterRole = ref('')
const filterOrg = ref('' as string | number | '')
const showCreate = ref(false)

const writable = computed(() => canWriteUsers(role.value))
const canAccount = computed(() => canCreateAccount(role.value))

const createForm = ref({
  name: '',
  role: 'advisor',
  org_id: '' as string | number | '',
  mobile: '',
  wecom_userid: '',
})
const editingId = ref<number | null>(null)
const editForm = ref({
  name: '',
  role: 'advisor',
  org_id: '' as string | number | '',
  status: 1,
  mobile: '',
  wecom_userid: '',
})
const accountUserId = ref<number | null>(null)
const accountUserName = ref('')
const accountForm = ref({ login_name: '', password: '' })
const resetPasswordUserId = ref<number | null>(null)
const resetPasswordUserName = ref('')
const resetPasswordForm = ref({ password: '' })

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
  if (!createForm.value.name.trim()) {
    flash.err('请填写姓名')
    return
  }
  busy.value = true
  try {
    await api('/admin/users', {
      method: 'POST',
      body: JSON.stringify({
        name: createForm.value.name.trim(),
        role: createForm.value.role,
        org_id: createForm.value.org_id === '' ? null : Number(createForm.value.org_id),
        mobile: createForm.value.mobile.trim() || null,
        wecom_userid: createForm.value.wecom_userid.trim() || null,
      }),
    })
    createForm.value = {
      name: '',
      role: 'advisor',
      org_id: me.value?.org_id ?? '',
      mobile: '',
      wecom_userid: '',
    }
    showCreate.value = false
    flash.ok('员工已创建')
    await load()
  } catch (e: any) {
    flash.err(e?.message || '创建失败')
  } finally {
    busy.value = false
  }
}

function startEdit(u: any) {
  accountUserId.value = null
  resetPasswordUserId.value = null
  editingId.value = u.id
  editForm.value = {
    name: u.name || '',
    role: u.role || 'advisor',
    org_id: u.org_id ?? '',
    status: u.status ?? 1,
    mobile: u.mobile || '',
    wecom_userid: u.wecom_userid || '',
  }
}

function cancelEdit() {
  editingId.value = null
}

async function saveEdit() {
  if (editingId.value == null) return
  if (!editForm.value.name.trim()) {
    flash.err('请填写姓名')
    return
  }
  busy.value = true
  try {
    await api(`/admin/users/${editingId.value}`, {
      method: 'PATCH',
      body: JSON.stringify({
        name: editForm.value.name.trim(),
        role: editForm.value.role,
        org_id: editForm.value.org_id === '' ? null : Number(editForm.value.org_id),
        status: Number(editForm.value.status),
        mobile: editForm.value.mobile.trim() || null,
        wecom_userid: editForm.value.wecom_userid.trim() || null,
      }),
    })
    editingId.value = null
    flash.ok('员工已更新')
    await load()
  } catch (e: any) {
    flash.err(e?.message || '更新失败')
  } finally {
    busy.value = false
  }
}

function openAccount(u: any) {
  editingId.value = null
  resetPasswordUserId.value = null
  accountUserId.value = u.id
  accountUserName.value = u.name || ''
  accountForm.value = { login_name: '', password: '' }
}

function openResetPassword(u: any) {
  editingId.value = null
  accountUserId.value = null
  resetPasswordUserId.value = u.id
  resetPasswordUserName.value = u.name || ''
  resetPasswordForm.value = { password: '' }
}

async function createAccount() {
  if (accountUserId.value == null) return
  if (!accountForm.value.login_name.trim()) {
    flash.err('请填写登录名')
    return
  }
  if (!accountForm.value.password) {
    flash.err('请填写密码')
    return
  }
  if (accountForm.value.password.length < 6) {
    flash.err('密码至少 6 位')
    return
  }
  busy.value = true
  try {
    await api(`/admin/users/${accountUserId.value}/account`, {
      method: 'POST',
      body: JSON.stringify(accountForm.value),
    })
    flash.ok(`已为 ${accountUserName.value} 开通账号 ${accountForm.value.login_name}`)
    accountUserId.value = null
    accountUserName.value = ''
    await load()
  } catch (e: any) {
    flash.err(e?.message || '开账号失败')
  } finally {
    busy.value = false
  }
}

async function resetPassword() {
  if (resetPasswordUserId.value == null) return
  if (!resetPasswordForm.value.password) {
    flash.err('请填写新密码')
    return
  }
  if (resetPasswordForm.value.password.length < 6) {
    flash.err('密码至少 6 位')
    return
  }
  busy.value = true
  try {
    await api(`/admin/users/${resetPasswordUserId.value}/account/reset-password`, {
      method: 'POST',
      body: JSON.stringify({ password: resetPasswordForm.value.password }),
    })
    flash.ok(`已重置 ${resetPasswordUserName.value} 的密码`)
    resetPasswordUserId.value = null
    resetPasswordUserName.value = ''
    resetPasswordForm.value = { password: '' }
    await load()
  } catch (e: any) {
    flash.err(e?.message || '重置密码失败')
  } finally {
    busy.value = false
  }
}

async function removeUser(u: any) {
  if (!window.confirm(`确认软删除员工「${u.name}」？删除后将无法登录且不在列表显示。`)) return
  busy.value = true
  try {
    await api(`/admin/users/${u.id}`, { method: 'DELETE' })
    flash.ok('员工已删除')
    editingId.value = null
    accountUserId.value = null
    resetPasswordUserId.value = null
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
  await loadOrgs()
  await load()
})
</script>

<template>
  <section class="rounded-panel border border-line bg-white p-5 shadow-soft">
    <div class="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="font-display text-lg font-semibold">员工</h2>
        <FlashBanner class="mt-2" :message="flash.state.message" :kind="flash.state.kind" />
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <form class="flex flex-wrap items-center gap-2" @submit.prevent="onSearch">
          <input
            v-model="keyword"
            placeholder="姓名/手机…"
            class="rounded-control border border-line px-2.5 py-1.5 text-sm"
          />
          <select v-model="filterRole" class="rounded-control border border-line px-2.5 py-1.5 text-sm">
            <option value="">全部角色</option>
            <option value="admin">管理员</option>
            <option value="regional">区域主管</option>
            <option value="advisor">顾问</option>
          </select>
          <select v-model="filterOrg" class="rounded-control border border-line px-2.5 py-1.5 text-sm">
            <option value="">全部组织</option>
            <option v-for="o in orgs" :key="o.id" :value="o.id">{{ o.name }}</option>
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
          {{ showCreate ? '收起' : '新建员工' }}
        </button>
      </div>
    </div>

    <form
      v-if="showCreate && writable"
      class="mb-4 grid max-w-md gap-3 rounded-panel border border-line bg-stone-50 p-4"
      @submit.prevent="createUser"
    >
      <strong class="text-sm">新建员工</strong>
      <label class="grid gap-1 text-sm text-muted">
        姓名
        <input v-model="createForm.name" required class="rounded-control border border-line px-2.5 py-1.5 text-ink" />
      </label>
      <label class="grid gap-1 text-sm text-muted">
        角色
        <select v-model="createForm.role" class="rounded-control border border-line px-2.5 py-1.5 text-ink">
          <option v-for="r in roleOptions" :key="r.value" :value="r.value">{{ r.label }}</option>
        </select>
      </label>
      <label class="grid gap-1 text-sm text-muted">
        组织
        <select v-model="createForm.org_id" class="rounded-control border border-line px-2.5 py-1.5 text-ink">
          <option value="">默认</option>
          <option v-for="o in orgs" :key="o.id" :value="o.id">{{ o.name }}</option>
        </select>
      </label>
      <label class="grid gap-1 text-sm text-muted">
        手机
        <input v-model="createForm.mobile" class="rounded-control border border-line px-2.5 py-1.5 text-ink" />
      </label>
      <label class="grid gap-1 text-sm text-muted">
        企微 userid
        <input
          v-model="createForm.wecom_userid"
          placeholder="可选"
          class="rounded-control border border-line px-2.5 py-1.5 text-ink"
        />
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

    <p v-if="loading" class="mt-4 text-sm text-muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <EmptyState v-else-if="!(users?.items || []).length" title="暂无员工" />
    <template v-else>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="border-b border-line text-muted">
            <tr>
              <th class="pb-2 pr-3 font-medium">姓名</th>
              <th class="pb-2 pr-3 font-medium">角色</th>
              <th class="pb-2 pr-3 font-medium">组织</th>
              <th class="pb-2 pr-3 font-medium">手机</th>
              <th class="pb-2 pr-3 font-medium">企微 userid</th>
              <th class="pb-2 pr-3 font-medium">后台账号</th>
              <th class="pb-2 pr-3 font-medium">状态</th>
              <th class="pb-2 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="u in users.items"
              :key="u.id"
              class="border-b border-line/60 hover:bg-fjord-soft/40"
            >
              <td class="py-2 pr-3">
                <input
                  v-if="editingId === u.id"
                  v-model="editForm.name"
                  class="w-full rounded-control border border-line px-2 py-1 text-sm"
                />
                <template v-else>{{ u.name }}</template>
              </td>
              <td class="py-2 pr-3">
                <select
                  v-if="editingId === u.id"
                  v-model="editForm.role"
                  class="rounded-control border border-line px-2 py-1 text-sm"
                >
                  <option v-for="r in roleOptions" :key="r.value" :value="r.value">{{ r.label }}</option>
                </select>
                <template v-else>{{ roleLabel(u.role) }}</template>
              </td>
              <td class="py-2 pr-3">
                <select
                  v-if="editingId === u.id"
                  v-model="editForm.org_id"
                  class="rounded-control border border-line px-2 py-1 text-sm"
                >
                  <option value="">—</option>
                  <option v-for="o in orgs" :key="o.id" :value="o.id">{{ o.name }}</option>
                </select>
                <template v-else>{{ orgName(u.org_id) }}</template>
              </td>
              <td class="py-2 pr-3">
                <input
                  v-if="editingId === u.id"
                  v-model="editForm.mobile"
                  class="w-full rounded-control border border-line px-2 py-1 text-sm"
                />
                <template v-else>{{ u.mobile || '—' }}</template>
              </td>
              <td class="py-2 pr-3">
                <input
                  v-if="editingId === u.id"
                  v-model="editForm.wecom_userid"
                  class="w-full rounded-control border border-line px-2 py-1 text-sm"
                />
                <template v-else>{{ u.wecom_userid || '—' }}</template>
              </td>
              <td class="py-2 pr-3">{{ u.has_account ? '已开通' : '未开通' }}</td>
              <td class="py-2 pr-3">
                <select
                  v-if="editingId === u.id"
                  v-model.number="editForm.status"
                  class="rounded-control border border-line px-2 py-1 text-sm"
                >
                  <option :value="1">启用</option>
                  <option :value="0">停用</option>
                </select>
                <template v-else>{{ u.status === 1 ? '启用' : '停用' }}</template>
              </td>
              <td class="py-2">
                <div class="flex flex-wrap gap-1.5">
                  <template v-if="writable && editingId === u.id">
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
                      @click="cancelEdit"
                    >
                      <UiIcon :icon="X" :size="14" />
                      取消
                    </button>
                  </template>
                  <template v-else>
                    <button
                      v-if="writable"
                      type="button"
                      :disabled="busy"
                      class="inline-flex items-center gap-1 rounded-control border border-line bg-white px-2.5 py-1 text-xs text-ink hover:bg-stone-50 disabled:opacity-50"
                      :aria-label="`编辑员工 ${u.name}`"
                      @click="startEdit(u)"
                    >
                      <UiIcon :icon="Pencil" :size="14" />
                      编辑
                    </button>
                    <button
                      v-if="canAccount && !u.has_account"
                      type="button"
                      :disabled="busy"
                      class="inline-flex items-center gap-1 rounded-control border border-line bg-white px-2.5 py-1 text-xs text-ink hover:bg-stone-50 disabled:opacity-50"
                      :aria-label="`为 ${u.name} 开通账号`"
                      @click="openAccount(u)"
                    >
                      <UiIcon :icon="UserPlus" :size="14" />
                      开账号
                    </button>
                    <button
                      v-if="canAccount && u.has_account"
                      type="button"
                      :disabled="busy"
                      class="inline-flex items-center gap-1 rounded-control border border-line bg-white px-2.5 py-1 text-xs text-ink hover:bg-stone-50 disabled:opacity-50"
                      :aria-label="`重置 ${u.name} 的密码`"
                      @click="openResetPassword(u)"
                    >
                      <UiIcon :icon="KeyRound" :size="14" />
                      重置密码
                    </button>
                    <button
                      v-if="writable"
                      type="button"
                      :disabled="busy"
                      class="inline-flex items-center gap-1 rounded-control border border-line bg-white px-2.5 py-1 text-xs text-danger hover:bg-stone-50 disabled:opacity-50"
                      :aria-label="`删除员工 ${u.name}`"
                      @click="removeUser(u)"
                    >
                      <UiIcon :icon="Trash2" :size="14" />
                      删除
                    </button>
                  </template>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div
        v-if="accountUserId != null"
        class="mt-4 grid max-w-md gap-3 rounded-panel border border-line bg-stone-50 p-4"
      >
        <strong class="text-sm">开通后台账号 · {{ accountUserName }}</strong>
        <label class="grid gap-1 text-sm text-muted">
          登录名
          <input v-model="accountForm.login_name" class="rounded-control border border-line px-2.5 py-1.5 text-ink" />
        </label>
        <label class="grid gap-1 text-sm text-muted">
          密码
          <input
            v-model="accountForm.password"
            type="password"
            class="rounded-control border border-line px-2.5 py-1.5 text-ink"
          />
        </label>
        <div class="flex gap-2">
          <button
            type="button"
            :disabled="busy"
            class="inline-flex items-center gap-1.5 rounded-control bg-fjord px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
            @click="createAccount"
          >
            <UiIcon :icon="UserPlus" :size="14" />
            {{ busy ? '开通中…' : '开通' }}
          </button>
          <button
            type="button"
            :disabled="busy"
            class="inline-flex items-center gap-1.5 rounded-control border border-line bg-white px-3 py-1.5 text-sm text-ink hover:bg-stone-50 disabled:opacity-50"
            @click="accountUserId = null"
          >
            <UiIcon :icon="X" :size="14" />
            取消
          </button>
        </div>
      </div>

      <div
        v-if="resetPasswordUserId != null"
        class="mt-4 grid max-w-md gap-3 rounded-panel border border-line bg-stone-50 p-4"
      >
        <strong class="text-sm">重置密码 · {{ resetPasswordUserName }}</strong>
        <label class="grid gap-1 text-sm text-muted">
          新密码
          <input
            v-model="resetPasswordForm.password"
            type="password"
            class="rounded-control border border-line px-2.5 py-1.5 text-ink"
          />
        </label>
        <div class="flex gap-2">
          <button
            type="button"
            :disabled="busy"
            class="inline-flex items-center gap-1.5 rounded-control bg-fjord px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
            @click="resetPassword"
          >
            <UiIcon :icon="KeyRound" :size="14" />
            {{ busy ? '重置中…' : '重置' }}
          </button>
          <button
            type="button"
            :disabled="busy"
            class="inline-flex items-center gap-1.5 rounded-control border border-line bg-white px-3 py-1.5 text-sm text-ink hover:bg-stone-50 disabled:opacity-50"
            @click="resetPasswordUserId = null"
          >
            <UiIcon :icon="X" :size="14" />
            取消
          </button>
        </div>
      </div>

      <PaginationBar
        :page="page"
        :page-size="pageSize"
        :total="users.total || 0"
        @update:page="(n) => (page = n)"
      />
    </template>
  </section>
</template>
