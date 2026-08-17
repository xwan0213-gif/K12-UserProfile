<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Pencil, Plus, Save, Trash2, X } from '@lucide/vue'
import EmptyState from '../components/EmptyState.vue'
import FlashBanner from '../components/FlashBanner.vue'
import UiIcon from '../components/UiIcon.vue'
import { useFlash } from '../composables/useFlash'
import { useAuth } from '../composables/useAuth'
import { canWriteScripts } from '../nav'

const { api, role } = useAuth()
const flash = useFlash()
const scripts = ref<any>(null)
const error = ref('')
const loading = ref(true)
const busy = ref(false)
const writable = computed(() => canWriteScripts(role.value))
const filterScene = ref('')
const filterEnabled = ref('')

const scriptForm = ref({
  scene: 'sales',
  stage: 'junior' as string | null,
  title: '',
  content: '',
  enabled: true,
})
const editingId = ref<number | null>(null)
const editForm = ref({
  scene: 'sales',
  stage: 'junior' as string | null,
  title: '',
  content: '',
  enabled: true,
})

function truncateOneLine(text?: string | null) {
  if (!text) return '—'
  const single = text.replace(/\s+/g, ' ').trim()
  if (single.length <= 60) return single
  return `${single.slice(0, 60)}…`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const qs = new URLSearchParams()
    if (filterScene.value) qs.set('scene', filterScene.value)
    if (filterEnabled.value !== '') qs.set('enabled', filterEnabled.value)
    const q = qs.toString()
    scripts.value = await api(`/admin/script-templates${q ? `?${q}` : ''}`)
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function createScript() {
  if (!scriptForm.value.title.trim()) {
    flash.err('请填写标题')
    return
  }
  if (!scriptForm.value.content.trim()) {
    flash.err('请填写正文')
    return
  }
  busy.value = true
  try {
    await api('/admin/script-templates', {
      method: 'POST',
      body: JSON.stringify({
        ...scriptForm.value,
        title: scriptForm.value.title.trim(),
        content: scriptForm.value.content.trim(),
        stage: scriptForm.value.stage || null,
      }),
    })
    scriptForm.value.title = ''
    scriptForm.value.content = ''
    flash.ok('话术模板已创建')
    await load()
  } catch (e: any) {
    flash.err(e?.message || '创建失败')
  } finally {
    busy.value = false
  }
}

function startEdit(s: any) {
  editingId.value = s.id
  editForm.value = {
    scene: s.scene,
    stage: s.stage ?? null,
    title: s.title || '',
    content: s.content || '',
    enabled: !!s.enabled,
  }
}

async function saveEdit() {
  if (editingId.value == null) return
  if (!editForm.value.title.trim()) {
    flash.err('请填写标题')
    return
  }
  if (!editForm.value.content.trim()) {
    flash.err('请填写正文')
    return
  }
  busy.value = true
  try {
    await api(`/admin/script-templates/${editingId.value}`, {
      method: 'PATCH',
      body: JSON.stringify({
        scene: editForm.value.scene,
        stage: editForm.value.stage || null,
        title: editForm.value.title.trim(),
        content: editForm.value.content.trim(),
        enabled: editForm.value.enabled,
      }),
    })
    editingId.value = null
    flash.ok('模板已更新')
    await load()
  } catch (e: any) {
    flash.err(e?.message || '更新失败')
  } finally {
    busy.value = false
  }
}

async function disableScript(s: any) {
  if (!window.confirm('确认停用该话术模板？侧栏将不再推荐。')) return
  busy.value = true
  try {
    await api(`/admin/script-templates/${s.id}`, { method: 'DELETE' })
    flash.ok('已停用')
    await load()
  } catch (e: any) {
    flash.err(e?.message || '停用失败')
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
    <h2 class="font-display text-lg font-semibold">话术模板</h2>
    <FlashBanner class="mt-2" :message="flash.state.message" :kind="flash.state.kind" />

    <form class="mt-3 flex flex-wrap items-center gap-2" @submit.prevent="load">
      <select v-model="filterScene" class="rounded-control border border-line px-2.5 py-1.5 text-sm">
        <option value="">全部场景</option>
        <option value="sales">销售</option>
        <option value="cs">客服</option>
      </select>
      <select v-model="filterEnabled" class="rounded-control border border-line px-2.5 py-1.5 text-sm">
        <option value="">全部状态</option>
        <option value="true">启用</option>
        <option value="false">停用</option>
      </select>
      <button
        type="submit"
        class="rounded-control border border-line bg-white px-3 py-1.5 text-sm text-ink hover:bg-stone-50 disabled:opacity-50"
      >
        筛选
      </button>
    </form>

    <p v-if="loading" class="mt-4 text-sm text-muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <template v-else>
      <form
        v-if="writable"
        class="mt-4 grid max-w-xl gap-3 rounded-panel border border-line bg-stone-50 p-4"
        @submit.prevent="createScript"
      >
        <strong class="text-sm">新建话术模板</strong>
        <label class="grid gap-1 text-sm text-muted">
          场景
          <select v-model="scriptForm.scene" class="rounded-control border border-line px-2.5 py-1.5 text-ink">
            <option value="sales">销售</option>
            <option value="cs">客服</option>
          </select>
        </label>
        <label class="grid gap-1 text-sm text-muted">
          学段
          <select v-model="scriptForm.stage" class="rounded-control border border-line px-2.5 py-1.5 text-ink">
            <option value="primary">小学</option>
            <option value="junior">初中</option>
            <option value="senior">高中</option>
            <option :value="null">通用</option>
          </select>
        </label>
        <label class="grid gap-1 text-sm text-muted">
          标题
          <input v-model="scriptForm.title" required class="rounded-control border border-line px-2.5 py-1.5 text-ink" />
        </label>
        <label class="grid gap-1 text-sm text-muted">
          正文
          <textarea
            v-model="scriptForm.content"
            rows="3"
            required
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
      <p v-else class="mt-4 text-sm text-muted">顾问账号仅可查看模板；新建/编辑/停用需管理员或区域主管。</p>

      <EmptyState v-if="!(scripts?.items || []).length" title="暂无模板" />
      <div v-else class="mt-4 overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="border-b border-line text-muted">
            <tr>
              <th class="pb-2 pr-3 font-medium">场景</th>
              <th class="pb-2 pr-3 font-medium">学段</th>
              <th class="pb-2 pr-3 font-medium">标题</th>
              <th class="pb-2 pr-3 font-medium">正文</th>
              <th class="pb-2 pr-3 font-medium">启用</th>
              <th class="pb-2 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="s in scripts.items"
              :key="s.id"
              class="border-b border-line/60 hover:bg-fjord-soft/40"
            >
              <template v-if="editingId === s.id">
                <td class="py-2 pr-3">
                  <select v-model="editForm.scene" class="rounded-control border border-line px-2 py-1 text-sm">
                    <option value="sales">销售</option>
                    <option value="cs">客服</option>
                  </select>
                </td>
                <td class="py-2 pr-3">
                  <select v-model="editForm.stage" class="rounded-control border border-line px-2 py-1 text-sm">
                    <option value="primary">小学</option>
                    <option value="junior">初中</option>
                    <option value="senior">高中</option>
                    <option :value="null">通用</option>
                  </select>
                </td>
                <td colspan="2" class="py-2 pr-3">
                  <input
                    v-model="editForm.title"
                    placeholder="标题"
                    class="mb-1 w-full rounded-control border border-line px-2 py-1 text-sm"
                  />
                  <textarea
                    v-model="editForm.content"
                    rows="2"
                    class="w-full rounded-control border border-line px-2 py-1 text-sm"
                  />
                  <label class="mt-1 flex items-center gap-2 text-xs text-muted">
                    <input v-model="editForm.enabled" type="checkbox" />
                    启用
                  </label>
                </td>
                <td class="py-2 pr-3">{{ editForm.enabled ? '是' : '否' }}</td>
                <td class="py-2">
                  <div class="flex flex-wrap gap-1.5">
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
                  </div>
                </td>
              </template>
              <template v-else>
                <td class="py-2 pr-3">{{ s.scene }}</td>
                <td class="py-2 pr-3">{{ s.stage || '通用' }}</td>
                <td class="py-2 pr-3">{{ s.title }}</td>
                <td class="max-w-xs py-2 pr-3 text-muted">
                  <span class="block truncate" :title="s.content">{{ truncateOneLine(s.content) }}</span>
                </td>
                <td class="py-2 pr-3">{{ s.enabled ? '是' : '否' }}</td>
                <td class="py-2">
                  <div v-if="writable" class="flex flex-wrap gap-1.5">
                    <button
                      type="button"
                      :disabled="busy"
                      class="inline-flex items-center gap-1 rounded-control border border-line bg-white px-2.5 py-1 text-xs text-ink hover:bg-stone-50 disabled:opacity-50"
                      :aria-label="`编辑话术 ${s.title}`"
                      @click="startEdit(s)"
                    >
                      <UiIcon :icon="Pencil" :size="14" />
                      编辑
                    </button>
                    <button
                      v-if="s.enabled"
                      type="button"
                      :disabled="busy"
                      class="inline-flex items-center gap-1 rounded-control border border-line bg-white px-2.5 py-1 text-xs text-danger hover:bg-stone-50 disabled:opacity-50"
                      :aria-label="`停用话术 ${s.title}`"
                      @click="disableScript(s)"
                    >
                      <UiIcon :icon="Trash2" :size="14" />
                      停用
                    </button>
                  </div>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </section>
</template>
