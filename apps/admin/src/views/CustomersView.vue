<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Inbox, Plus } from '@lucide/vue'
import EmptyState from '../components/EmptyState.vue'
import FlashBanner from '../components/FlashBanner.vue'
import PaginationBar from '../components/PaginationBar.vue'
import UiIcon from '../components/UiIcon.vue'
import { useFlash } from '../composables/useFlash'
import { useAuth } from '../composables/useAuth'
import { canWriteCustomers } from '../nav'

const router = useRouter()
const { api, role, me } = useAuth()
const flash = useFlash()
const customers = ref<any>(null)
const users = ref<any[]>([])
const tags = ref<any[]>([])
const error = ref('')
const loading = ref(true)
const busy = ref(false)
const keyword = ref('')
const grade = ref('')
const filterTagId = ref('' as string | number | '')
const filterOwnerId = ref('' as string | number | '')
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

function formatDateTime(iso?: string | null) {
  if (!iso) return '—'
  return iso.replace('T', ' ').replace('Z', '').slice(0, 16)
}

async function loadUsers() {
  if (role.value === 'advisor') return
  try {
    const data = await api('/admin/users?page=1&page_size=100')
    users.value = data?.items || []
  } catch {
    users.value = []
  }
}

async function loadTags() {
  try {
    const data = await api('/admin/tags')
    tags.value = data?.items || []
  } catch {
    tags.value = []
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
    if (filterTagId.value !== '') qs.set('tag_id', String(filterTagId.value))
    if (filterOwnerId.value !== '') qs.set('owner_user_id', String(filterOwnerId.value))
    customers.value = await api(`/admin/customers?${qs}`)
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function createCustomer() {
  if (!form.value.parent_name.trim()) {
    flash.err('请填写家长姓名')
    return
  }
  busy.value = true
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
    flash.ok('客户已创建')
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
    flash.err(e?.message || '创建失败')
  } finally {
    busy.value = false
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
  await Promise.all([loadUsers(), loadTags()])
  await load()
})
</script>

<template>
  <section class="rounded-panel border border-line bg-white p-5 shadow-soft">
    <div class="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="font-display text-lg font-semibold">客户</h2>
        <p class="mt-1 text-sm text-muted">查找并进入详情；可新建客户资料。</p>
        <FlashBanner class="mt-2" :message="flash.state.message" :kind="flash.state.kind" />
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <form class="flex flex-wrap items-center gap-2" @submit.prevent="onSearch">
          <input
            v-model="keyword"
            class="rounded-control border border-line px-2.5 py-1.5 text-sm"
            placeholder="搜索家长/学员…"
          />
          <input
            v-model="grade"
            class="rounded-control border border-line px-2.5 py-1.5 text-sm"
            placeholder="年级筛选…"
          />
          <select
            v-if="tags.length"
            v-model="filterTagId"
            class="rounded-control border border-line px-2.5 py-1.5 text-sm"
          >
            <option value="">全部标签</option>
            <option v-for="t in tags" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
          <select
            v-if="role !== 'advisor' && users.length"
            v-model="filterOwnerId"
            class="rounded-control border border-line px-2.5 py-1.5 text-sm"
          >
            <option value="">全部负责人</option>
            <option v-for="u in users" :key="u.id" :value="u.id">{{ u.name }}</option>
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
          <UiIcon :icon="Plus" :size="14" />
          {{ showCreate ? '收起' : '新建客户' }}
        </button>
      </div>
    </div>

    <form
      v-if="showCreate && writable"
      class="mb-4 grid max-w-md gap-3 rounded-panel border border-line bg-stone-50 p-4"
      @submit.prevent="createCustomer"
    >
      <strong class="text-sm">新建客户</strong>
      <label class="grid gap-1 text-sm text-muted">
        家长姓名
        <input
          v-model="form.parent_name"
          required
          class="rounded-control border border-line px-2.5 py-1.5 text-ink"
        />
      </label>
      <label class="grid gap-1 text-sm text-muted">
        学员姓名
        <input v-model="form.student_name" class="rounded-control border border-line px-2.5 py-1.5 text-ink" />
      </label>
      <label class="grid gap-1 text-sm text-muted">
        年级
        <input
          v-model="form.grade"
          placeholder="如 初二"
          class="rounded-control border border-line px-2.5 py-1.5 text-ink"
        />
      </label>
      <label class="grid gap-1 text-sm text-muted">
        学校
        <input v-model="form.school" class="rounded-control border border-line px-2.5 py-1.5 text-ink" />
      </label>
      <label class="grid gap-1 text-sm text-muted">
        学段
        <select v-model="form.stage" class="rounded-control border border-line px-2.5 py-1.5 text-ink">
          <option value="primary">小学</option>
          <option value="junior">初中</option>
          <option value="senior">高中</option>
        </select>
      </label>
      <label v-if="role !== 'advisor'" class="grid gap-1 text-sm text-muted">
        负责顾问
        <select v-model="form.owner_user_id" class="rounded-control border border-line px-2.5 py-1.5 text-ink">
          <option value="">默认自己</option>
          <option v-for="u in users" :key="u.id" :value="u.id">{{ u.name }}</option>
        </select>
      </label>
      <label class="grid gap-1 text-sm text-muted">
        备注
        <input v-model="form.remark" class="rounded-control border border-line px-2.5 py-1.5 text-ink" />
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
      v-else-if="!(customers?.items || []).length"
      title="暂无客户"
      hint="可点「新建客户」，或先 seed 演示数据。"
      :icon="Inbox"
    >
      <button
        v-if="writable"
        type="button"
        class="inline-flex items-center gap-1.5 rounded-control bg-fjord px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
        @click="showCreate = true"
      >
        <UiIcon :icon="Plus" :size="14" />
        新建客户
      </button>
    </EmptyState>
    <template v-else>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="border-b border-line text-muted">
            <tr>
              <th class="pb-2 pr-3 font-medium">家长/学员</th>
              <th class="pb-2 pr-3 font-medium">年级</th>
              <th class="pb-2 pr-3 font-medium">标签</th>
              <th class="pb-2 pr-3 font-medium">负责人</th>
              <th class="pb-2 pr-3 font-medium">最近联系</th>
              <th class="pb-2 font-medium">画像</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="c in customers.items"
              :key="c.id"
              tabindex="0"
              role="link"
              class="cursor-pointer border-b border-line/60 hover:bg-fjord-soft/40 focus:bg-fjord-soft/40 focus:outline-none focus:ring-2 focus:ring-fjord/30"
              @click="openCustomer(c.id)"
              @keydown.enter.prevent="openCustomer(c.id)"
              @keydown.space.prevent="openCustomer(c.id)"
            >
              <td class="py-2 pr-3">{{ c.parent_name }} / {{ c.student_name || '—' }}</td>
              <td class="py-2 pr-3">{{ c.grade || '—' }}</td>
              <td class="py-2 pr-3">{{ (c.tags || []).join('、') || '—' }}</td>
              <td class="py-2 pr-3">{{ c.owner_name || '—' }}</td>
              <td class="py-2 pr-3 text-muted">{{ formatDateTime(c.last_contact_at) }}</td>
              <td class="py-2">{{ c.profile_status || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <PaginationBar
        :page="page"
        :page-size="pageSize"
        :total="customers.total || 0"
        @update:page="(n) => (page = n)"
      />
    </template>
  </section>
</template>
