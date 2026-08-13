<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import EmptyState from '../components/EmptyState.vue'
import { useAuth } from '../composables/useAuth'
import { canWriteOrgs } from '../nav'

const { api, role } = useAuth()
const orgs = ref<any[]>([])
const error = ref('')
const loading = ref(true)
const flash = ref('')
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
  if (!form.value.name.trim()) return
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
    flash.value = '组织已创建'
    await load()
  } catch (e: any) {
    flash.value = e?.message || '创建失败'
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
    flash.value = '组织已更新'
    await load()
  } catch (e: any) {
    flash.value = e?.message || '更新失败'
  }
}

async function removeOrg(id: number) {
  if (!window.confirm('软删除该组织？')) return
  try {
    await api(`/admin/orgs/${id}`, { method: 'DELETE' })
    flash.value = '组织已删除'
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
    <h2>组织</h2>
    <p v-if="flash" class="muted">{{ flash }}</p>
    <p v-if="loading" class="muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <template v-else>
      <form v-if="writable" class="form" @submit.prevent="createOrg">
        <strong>新建组织</strong>
        <label>名称 <input v-model="form.name" required /></label>
        <label>
          上级
          <select v-model="form.parent_id">
            <option value="">无</option>
            <option v-for="o in orgs" :key="o.id" :value="o.id">{{ o.name }}</option>
          </select>
        </label>
        <label>编码 <input v-model="form.code" placeholder="可选" /></label>
        <button type="submit" class="primary">创建</button>
      </form>
      <p v-else class="muted">区域主管可查看组织；创建/改/删仅管理员。</p>

      <EmptyState v-if="!orgs.length" title="暂无组织" />
      <table v-else class="data">
        <thead>
          <tr><th>ID</th><th>名称</th><th>上级</th><th>编码</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="o in orgs" :key="o.id">
            <td>{{ o.id }}</td>
            <td>
              <template v-if="editingId === o.id">
                <input v-model="editForm.name" />
              </template>
              <template v-else>{{ o.name }}</template>
            </td>
            <td>
              <template v-if="editingId === o.id">
                <select v-model="editForm.parent_id">
                  <option value="">无</option>
                  <option
                    v-for="p in orgs.filter((x) => x.id !== o.id)"
                    :key="p.id"
                    :value="p.id"
                  >
                    {{ p.name }}
                  </option>
                </select>
              </template>
              <template v-else>{{ orgName(o.parent_id) }}</template>
            </td>
            <td>
              <template v-if="editingId === o.id">
                <input v-model="editForm.code" />
              </template>
              <template v-else>{{ o.code || '—' }}</template>
            </td>
            <td class="actions">
              <template v-if="writable && editingId === o.id">
                <button type="button" class="primary" @click="saveEdit">保存</button>
                <button type="button" @click="editingId = null">取消</button>
              </template>
              <template v-else-if="writable">
                <button type="button" @click="startEdit(o)">改</button>
                <button type="button" @click="removeOrg(o.id)">删</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </template>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 10px; font-size: 1.05rem; }
.form {
  display: grid;
  gap: 8px;
  max-width: 420px;
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
.form input,
.form select,
td input,
td select {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 8px;
  color: var(--ink);
  width: 100%;
}
.actions { display: flex; gap: 6px; flex-wrap: wrap; }
</style>
