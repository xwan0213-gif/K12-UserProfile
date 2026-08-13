<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import EmptyState from '../components/EmptyState.vue'
import { useAuth } from '../composables/useAuth'
import { canWriteTags } from '../nav'

const { api, role } = useAuth()
const tags = ref<any>(null)
const tagStats = ref<any>(null)
const error = ref('')
const loading = ref(true)
const flash = ref('')
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
  if (!form.value.name.trim()) return
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
    flash.value = '标签已创建'
    await load()
  } catch (e: any) {
    flash.value = e?.message || '创建失败'
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
    flash.value = '标签已更新'
    await load()
  } catch (e: any) {
    flash.value = e?.message || '更新失败'
  }
}

async function removeTag(id: number) {
  if (!window.confirm('软删除该标签？词表中将不再显示。')) return
  try {
    await api(`/admin/tags/${id}`, { method: 'DELETE' })
    flash.value = '标签已删除'
    editingId.value = null
    await load()
  } catch (e: any) {
    flash.value = e?.message || '删除失败'
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <section class="card">
    <h2>标签体系</h2>
    <p v-if="flash" class="muted">{{ flash }}</p>
    <p v-if="loading" class="muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <template v-else>
      <form v-if="writable" class="form" @submit.prevent="createTag">
        <strong>新建标签</strong>
        <label>名称 <input v-model="form.name" required /></label>
        <label>说明 <input v-model="form.description" /></label>
        <label>SOP <textarea v-model="form.sop_text" rows="2" /></label>
        <label>排序 <input v-model.number="form.sort_order" type="number" /></label>
        <label class="check"><input v-model="form.enabled" type="checkbox" /> 启用</label>
        <button type="submit" class="primary">创建</button>
      </form>
      <p v-else class="muted">顾问仅可查看标签；新建/编辑需管理员或区域主管。</p>

      <EmptyState v-if="!(tags?.items || []).length" title="词表为空" />
      <table v-else class="data">
        <thead>
          <tr><th>名称</th><th>SOP</th><th>客户数</th><th>启用</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="t in tags.items" :key="t.id">
            <td>
              <template v-if="editingId === t.id">
                <input v-model="editForm.name" />
              </template>
              <template v-else>{{ t.name }}</template>
            </td>
            <td>
              <template v-if="editingId === t.id">
                <textarea v-model="editForm.sop_text" rows="2" />
              </template>
              <template v-else>{{ t.sop_text || '—' }}</template>
            </td>
            <td>{{ t.customer_count ?? '—' }}</td>
            <td>
              <template v-if="editingId === t.id">
                <input v-model="editForm.enabled" type="checkbox" />
              </template>
              <template v-else>{{ t.enabled ? '是' : '否' }}</template>
            </td>
            <td class="actions">
              <template v-if="writable && editingId === t.id">
                <button type="button" class="primary" @click="saveEdit">保存</button>
                <button type="button" @click="editingId = null">取消</button>
              </template>
              <template v-else-if="writable">
                <button type="button" @click="startEdit(t)">改</button>
                <button type="button" @click="removeTag(t.id)">删</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>

      <h3>分布</h3>
      <ul v-if="(tagStats?.items || []).length">
        <li v-for="s in tagStats.items" :key="s.tag_id">
          {{ s.name }}：{{ s.customer_count }}
        </li>
      </ul>
      <EmptyState v-else title="暂无分布统计" />
    </template>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 10px; font-size: 1.05rem; }
h3 { margin: 14px 0 6px; font-size: 0.95rem; }
.form {
  display: grid;
  gap: 8px;
  max-width: 520px;
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
.form .check {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
}
.form input,
.form textarea,
td input,
td textarea {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 8px;
  color: var(--ink);
  width: 100%;
}
.actions { display: flex; gap: 6px; }
</style>
