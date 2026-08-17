<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Pencil, Plus, Save, Trash2, X } from '@lucide/vue'
import EmptyState from '../components/EmptyState.vue'
import FlashBanner from '../components/FlashBanner.vue'
import UiIcon from '../components/UiIcon.vue'
import { useFlash } from '../composables/useFlash'
import { useAuth } from '../composables/useAuth'
import { canWriteOrgs } from '../nav'

const { api, role } = useAuth()
const flash = useFlash()
const orgs = ref<any[]>([])
const error = ref('')
const loading = ref(true)
const busy = ref(false)
const showCreate = ref(false)
const writable = computed(() => canWriteOrgs(role.value))

const form = ref({ name: '', parent_id: '' as string | number | '', code: '' })
const editingId = ref<number | null>(null)
const editForm = ref({ name: '', parent_id: '' as string | number | '', code: '' })

function orgName(id?: number | null) {
  if (id == null) return '—'
  return orgs.value.find((o) => o.id === id)?.name || `#${id}`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await api('/admin/orgs')
    orgs.value = data?.items || []
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function createOrg() {
  if (!form.value.name.trim()) {
    flash.err('请填写组织名称')
    return
  }
  busy.value = true
  try {
    await api('/admin/orgs', {
      method: 'POST',
      body: JSON.stringify({
        name: form.value.name.trim(),
        parent_id: form.value.parent_id === '' ? null : Number(form.value.parent_id),
        code: form.value.code.trim() || null,
      }),
    })
    form.value = { name: '', parent_id: '', code: '' }
    showCreate.value = false
    flash.ok('组织已创建')
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
    name: o.name || '',
    parent_id: o.parent_id ?? '',
    code: o.code || '',
  }
}

async function saveEdit() {
  if (editingId.value == null) return
  if (!editForm.value.name.trim()) {
    flash.err('请填写组织名称')
    return
  }
  busy.value = true
  try {
    await api(`/admin/orgs/${editingId.value}`, {
      method: 'PATCH',
      body: JSON.stringify({
        name: editForm.value.name.trim(),
        parent_id:
          editForm.value.parent_id === '' ? null : Number(editForm.value.parent_id),
        code: editForm.value.code.trim() || null,
      }),
    })
    editingId.value = null
    flash.ok('组织已更新')
    await load()
  } catch (e: any) {
    flash.err(e?.message || '更新失败')
  } finally {
    busy.value = false
  }
}

async function removeOrg(o: any) {
  if (!window.confirm(`确认软删除组织「${o.name}」？删除后将不在列表显示，下属员工需另行调整。`)) return
  busy.value = true
  try {
    await api(`/admin/orgs/${o.id}`, { method: 'DELETE' })
    flash.ok('组织已删除')
    editingId.value = null
    await load()
  } catch (e: any) {
    flash.err(e?.message || '删除失败')
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <section class="rounded-panel border border-line bg-white p-5 shadow-soft">
    <div class="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="font-display text-lg font-semibold">组织</h2>
        <FlashBanner class="mt-2" :message="flash.state.message" :kind="flash.state.kind" />
      </div>
      <button
        v-if="writable"
        type="button"
        class="inline-flex items-center gap-1.5 rounded-control bg-fjord px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
        @click="showCreate = !showCreate"
      >
        <UiIcon :icon="showCreate ? X : Plus" :size="14" />
        {{ showCreate ? '收起' : '新建组织' }}
      </button>
    </div>

    <p v-if="loading" class="text-sm text-muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <template v-else>
      <form
        v-if="showCreate && writable"
        class="mb-4 grid max-w-md gap-3 rounded-panel border border-line bg-stone-50 p-4"
        @submit.prevent="createOrg"
      >
        <strong class="text-sm">新建组织</strong>
        <label class="grid gap-1 text-sm text-muted">
          名称
          <input v-model="form.name" required class="rounded-control border border-line px-2.5 py-1.5 text-ink" />
        </label>
        <label class="grid gap-1 text-sm text-muted">
          上级
          <select v-model="form.parent_id" class="rounded-control border border-line px-2.5 py-1.5 text-ink">
            <option value="">无</option>
            <option v-for="o in orgs" :key="o.id" :value="o.id">{{ o.name }}</option>
          </select>
        </label>
        <label class="grid gap-1 text-sm text-muted">
          编码
          <input
            v-model="form.code"
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
      <p v-else-if="!writable" class="text-sm text-muted">区域主管可查看组织；创建/编辑/删除仅管理员。</p>

      <EmptyState v-if="!orgs.length" title="暂无组织" />
      <div v-else class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="border-b border-line text-muted">
            <tr>
              <th class="pb-2 pr-3 font-medium">ID</th>
              <th class="pb-2 pr-3 font-medium">名称</th>
              <th class="pb-2 pr-3 font-medium">上级</th>
              <th class="pb-2 pr-3 font-medium">编码</th>
              <th class="pb-2 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="o in orgs"
              :key="o.id"
              class="border-b border-line/60 hover:bg-fjord-soft/40"
            >
              <td class="py-2 pr-3">{{ o.id }}</td>
              <td class="py-2 pr-3">
                <input
                  v-if="editingId === o.id"
                  v-model="editForm.name"
                  class="w-full rounded-control border border-line px-2 py-1 text-sm"
                />
                <template v-else>{{ o.name }}</template>
              </td>
              <td class="py-2 pr-3">
                <select
                  v-if="editingId === o.id"
                  v-model="editForm.parent_id"
                  class="rounded-control border border-line px-2 py-1 text-sm"
                >
                  <option value="">无</option>
                  <option
                    v-for="p in orgs.filter((x) => x.id !== o.id)"
                    :key="p.id"
                    :value="p.id"
                  >
                    {{ p.name }}
                  </option>
                </select>
                <template v-else>{{ orgName(o.parent_id) }}</template>
              </td>
              <td class="py-2 pr-3">
                <input
                  v-if="editingId === o.id"
                  v-model="editForm.code"
                  class="w-full rounded-control border border-line px-2 py-1 text-sm"
                />
                <template v-else>{{ o.code || '—' }}</template>
              </td>
              <td class="py-2">
                <div v-if="writable" class="flex flex-wrap gap-1.5">
                  <template v-if="editingId === o.id">
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
                  </template>
                  <template v-else>
                    <button
                      type="button"
                      :disabled="busy"
                      class="inline-flex items-center gap-1 rounded-control border border-line bg-white px-2.5 py-1 text-xs text-ink hover:bg-stone-50 disabled:opacity-50"
                      :aria-label="`编辑组织 ${o.name}`"
                      @click="startEdit(o)"
                    >
                      <UiIcon :icon="Pencil" :size="14" />
                      编辑
                    </button>
                    <button
                      type="button"
                      :disabled="busy"
                      class="inline-flex items-center gap-1 rounded-control border border-line bg-white px-2.5 py-1 text-xs text-danger hover:bg-stone-50 disabled:opacity-50"
                      :aria-label="`删除组织 ${o.name}`"
                      @click="removeOrg(o)"
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
    </template>
  </section>
</template>
