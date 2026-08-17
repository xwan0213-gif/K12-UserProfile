<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Pencil, Plus, Save, Trash2, X } from '@lucide/vue'
import EmptyState from '../components/EmptyState.vue'
import FlashBanner from '../components/FlashBanner.vue'
import UiIcon from '../components/UiIcon.vue'
import { useFlash } from '../composables/useFlash'
import { useAuth } from '../composables/useAuth'
import { canWriteTags } from '../nav'

const { api, role } = useAuth()
const flash = useFlash()
const tags = ref<any>(null)
const tagStats = ref<any>(null)
const error = ref('')
const loading = ref(true)
const busy = ref(false)
const writable = computed(() => canWriteTags(role.value))

const form = ref({
  name: '',
  description: '',
  sop_text: '',
  enabled: true,
  sort_order: 0,
})
const editingId = ref<number | null>(null)
const editForm = ref({
  name: '',
  description: '',
  sop_text: '',
  enabled: true,
  sort_order: 0,
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    tags.value = await api('/admin/tags')
    tagStats.value = await api('/admin/tags/stats')
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function createTag() {
  if (!form.value.name.trim()) {
    flash.err('请填写标签名称')
    return
  }
  busy.value = true
  try {
    await api('/admin/tags', {
      method: 'POST',
      body: JSON.stringify({
        name: form.value.name.trim(),
        description: form.value.description.trim() || null,
        sop_text: form.value.sop_text.trim() || null,
        enabled: form.value.enabled,
        sort_order: Number(form.value.sort_order) || 0,
      }),
    })
    form.value = { name: '', description: '', sop_text: '', enabled: true, sort_order: 0 }
    flash.ok('标签已创建')
    await load()
  } catch (e: any) {
    flash.err(e?.message || '创建失败')
  } finally {
    busy.value = false
  }
}

function startEdit(t: any) {
  editingId.value = t.id
  editForm.value = {
    name: t.name || '',
    description: t.description || '',
    sop_text: t.sop_text || '',
    enabled: !!t.enabled,
    sort_order: t.sort_order ?? 0,
  }
}

async function saveEdit() {
  if (editingId.value == null) return
  if (!editForm.value.name.trim()) {
    flash.err('请填写标签名称')
    return
  }
  busy.value = true
  try {
    await api(`/admin/tags/${editingId.value}`, {
      method: 'PATCH',
      body: JSON.stringify({
        name: editForm.value.name.trim(),
        description: editForm.value.description.trim() || null,
        sop_text: editForm.value.sop_text.trim() || null,
        enabled: editForm.value.enabled,
        sort_order: Number(editForm.value.sort_order) || 0,
      }),
    })
    editingId.value = null
    flash.ok('标签已更新')
    await load()
  } catch (e: any) {
    flash.err(e?.message || '更新失败')
  } finally {
    busy.value = false
  }
}

async function removeTag(t: any) {
  if (!window.confirm(`确认软删除标签「${t.name}」？词表中将不再显示。`)) return
  busy.value = true
  try {
    await api(`/admin/tags/${t.id}`, { method: 'DELETE' })
    flash.ok('标签已删除')
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
    <h2 class="font-display text-lg font-semibold">标签体系</h2>
    <FlashBanner class="mt-2" :message="flash.state.message" :kind="flash.state.kind" />
    <p v-if="loading" class="mt-4 text-sm text-muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <template v-else>
      <form
        v-if="writable"
        class="mt-4 grid max-w-lg gap-3 rounded-panel border border-line bg-stone-50 p-4"
        @submit.prevent="createTag"
      >
        <strong class="text-sm">新建标签</strong>
        <label class="grid gap-1 text-sm text-muted">
          名称
          <input v-model="form.name" required class="rounded-control border border-line px-2.5 py-1.5 text-ink" />
        </label>
        <label class="grid gap-1 text-sm text-muted">
          说明
          <input v-model="form.description" class="rounded-control border border-line px-2.5 py-1.5 text-ink" />
        </label>
        <label class="grid gap-1 text-sm text-muted">
          SOP
          <textarea v-model="form.sop_text" rows="2" class="rounded-control border border-line px-2.5 py-1.5 text-ink" />
        </label>
        <label class="grid gap-1 text-sm text-muted">
          排序
          <input
            v-model.number="form.sort_order"
            type="number"
            class="rounded-control border border-line px-2.5 py-1.5 text-ink"
          />
        </label>
        <label class="flex items-center gap-2 text-sm text-muted">
          <input v-model="form.enabled" type="checkbox" />
          启用
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
      <p v-else class="mt-4 text-sm text-muted">顾问仅可查看标签；新建/编辑需管理员或区域主管。</p>

      <EmptyState v-if="!(tags?.items || []).length" title="词表为空" />
      <div v-else class="mt-4 overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="border-b border-line text-muted">
            <tr>
              <th class="pb-2 pr-3 font-medium">名称</th>
              <th class="pb-2 pr-3 font-medium">说明</th>
              <th class="pb-2 pr-3 font-medium">SOP</th>
              <th class="pb-2 pr-3 font-medium">排序</th>
              <th class="pb-2 pr-3 font-medium">客户数</th>
              <th class="pb-2 pr-3 font-medium">启用</th>
              <th class="pb-2 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="t in tags.items"
              :key="t.id"
              class="border-b border-line/60 hover:bg-fjord-soft/40"
            >
              <td class="py-2 pr-3">
                <input
                  v-if="editingId === t.id"
                  v-model="editForm.name"
                  class="w-full rounded-control border border-line px-2 py-1 text-sm"
                />
                <template v-else>{{ t.name }}</template>
              </td>
              <td class="py-2 pr-3">
                <input
                  v-if="editingId === t.id"
                  v-model="editForm.description"
                  class="w-full rounded-control border border-line px-2 py-1 text-sm"
                />
                <template v-else>{{ t.description || '—' }}</template>
              </td>
              <td class="py-2 pr-3">
                <textarea
                  v-if="editingId === t.id"
                  v-model="editForm.sop_text"
                  rows="2"
                  class="w-full rounded-control border border-line px-2 py-1 text-sm"
                />
                <template v-else>{{ t.sop_text || '—' }}</template>
              </td>
              <td class="py-2 pr-3">
                <input
                  v-if="editingId === t.id"
                  v-model.number="editForm.sort_order"
                  type="number"
                  class="w-20 rounded-control border border-line px-2 py-1 text-sm"
                />
                <template v-else>{{ t.sort_order ?? 0 }}</template>
              </td>
              <td class="py-2 pr-3">{{ t.customer_count ?? '—' }}</td>
              <td class="py-2 pr-3">
                <input v-if="editingId === t.id" v-model="editForm.enabled" type="checkbox" />
                <template v-else>{{ t.enabled ? '是' : '否' }}</template>
              </td>
              <td class="py-2">
                <div v-if="writable" class="flex gap-1.5">
                  <template v-if="editingId === t.id">
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
                      :aria-label="`编辑标签 ${t.name}`"
                      @click="startEdit(t)"
                    >
                      <UiIcon :icon="Pencil" :size="14" />
                      编辑
                    </button>
                    <button
                      type="button"
                      :disabled="busy"
                      class="inline-flex items-center gap-1 rounded-control border border-line bg-white px-2.5 py-1 text-xs text-danger hover:bg-stone-50 disabled:opacity-50"
                      :aria-label="`删除标签 ${t.name}`"
                      @click="removeTag(t)"
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

      <h3 class="mb-2 mt-5 font-display text-base font-semibold">分布</h3>
      <ul v-if="(tagStats?.items || []).length" class="list-none space-y-1 p-0 text-sm text-muted">
        <li v-for="s in tagStats.items" :key="s.tag_id">{{ s.name }}：{{ s.customer_count }}</li>
      </ul>
      <EmptyState v-else title="暂无分布统计" />
    </template>
  </section>
</template>
